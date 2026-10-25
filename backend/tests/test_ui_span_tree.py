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
async def test_TRC_115_span_tree():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()
    trace_id = uuid.uuid4().hex
    root_id = uuid.uuid4().hex[:16]
    c1_id = uuid.uuid4().hex[:16]
    c2_id = uuid.uuid4().hex[:16]

    # Create root -> child1 -> child2 tree
    s_root = make_span(tenant, trace_id, root_id, None, "root_call", "gateway", now, 100_000_000)
    s_c1 = make_span(tenant, trace_id, c1_id, root_id, "service_call", "auth-svc", now + 10_000_000, 40_000_000)
    s_c2 = make_span(tenant, trace_id, c2_id, c1_id, "db_lookup", "postgres", now + 20_000_000, 10_000_000)

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s_root, s_c1, s_c2])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        spans = data["spans"]
        assert len(spans) == 3

        # Validate parent-child graph links
        span_map = {s["span_id"]: s for s in spans}
        assert span_map[root_id]["parent_span_id"] is None
        assert span_map[c1_id]["parent_span_id"] == root_id
        assert span_map[c2_id]["parent_span_id"] == c1_id
