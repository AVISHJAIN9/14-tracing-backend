import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_TRC_123_trace_links_viewer():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    linked_trace_id = uuid.uuid4().hex
    linked_span_id = uuid.uuid4().hex[:16]
    now = time.time_ns()

    span = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="payment-processor",
        name="capture_charge",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 60_000_000,
        duration_nanos=60_000_000,
        status_code="OK",
        attributes={"payment.gateway": "stripe"},
        events=[],
        links=[
            {
                "trace_id": linked_trace_id,
                "span_id": linked_span_id,
                "attributes": {"link.relation": "parent_order"}
            }
        ]
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
        retrieved_span = data["spans"][0]
        assert len(retrieved_span["links"]) == 1
        link = retrieved_span["links"][0]
        assert link["trace_id"] == linked_trace_id
        assert link["span_id"] == linked_span_id
        assert link["attributes"]["link.relation"] == "parent_order"
