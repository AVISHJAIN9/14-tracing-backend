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
async def test_TRC_117_dependency_graph():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()
    trace_id = uuid.uuid4().hex
    p_id = uuid.uuid4().hex[:16]
    c_id = uuid.uuid4().hex[:16]

    s1 = make_span(tenant, trace_id, p_id, None, "route_traffic", "edge-proxy", now, 50_000_000)
    s2 = make_span(tenant, trace_id, c_id, p_id, "process_order", "checkout-svc", now + 5_000_000, 30_000_000)

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s1, s2])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/dependencies", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        assert "dependencies" in data
        deps = data["dependencies"]
        assert any(d["caller"] == "edge-proxy" and d["callee"] == "checkout-svc" for d in deps)
