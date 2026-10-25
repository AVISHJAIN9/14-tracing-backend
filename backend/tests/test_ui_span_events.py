import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_TRC_121_span_event_viewer():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    events = [
        {"name": "cache_lookup", "time_unix_nano": now + 2_000_000, "attributes": {"cache.hit": False}},
        {"name": "db_query_start", "time_unix_nano": now + 5_000_000, "attributes": {"sql.table": "orders"}}
    ]

    span = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="order-api",
        name="get_order",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 20_000_000,
        duration_nanos=20_000_000,
        status_code="OK",
        attributes={},
        events=events,
        links=[]
    )

    async with get_db_session(tenant_id=tenant) as session:
        session.add(span)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        assert len(data["spans"]) == 1
        retrieved_events = data["spans"][0]["events"]
        assert len(retrieved_events) == 2
        assert retrieved_events[0]["name"] == "cache_lookup"
        assert retrieved_events[1]["name"] == "db_query_start"
