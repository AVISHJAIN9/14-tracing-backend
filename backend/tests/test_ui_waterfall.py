import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, span_id, parent_id, name, service, start_ns, duration_ns):
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_id,
        service_name=service,
        name=name,
        kind="SERVER",
        start_time_unix_nano=start_ns,
        end_time_unix_nano=start_ns + duration_ns,
        duration_nanos=duration_ns,
        status_code="OK",
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_114_waterfall_timeline():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t_start = 1_000_000_000_000_000_000
    trace_id = uuid.uuid4().hex
    s1_id = uuid.uuid4().hex[:16]
    s2_id = uuid.uuid4().hex[:16]

    s1 = make_span(tenant, trace_id, s1_id, None, "handle_request", "web-gateway", t_start, 50_000_000)
    s2 = make_span(tenant, trace_id, s2_id, s1_id, "query_db", "user-db", t_start + 10_000_000, 20_000_000)

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s1, s2])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        spans = data["spans"]
        assert len(spans) == 2

        # Verify waterfall timeline attributes
        min_start = min(s["start_time_unix_nano"] for s in spans)
        assert min_start == t_start

        for s in spans:
            offset = s["start_time_unix_nano"] - min_start
            assert offset >= 0
            assert s["duration_nanos"] > 0
            assert s["end_time_unix_nano"] >= s["start_time_unix_nano"]
