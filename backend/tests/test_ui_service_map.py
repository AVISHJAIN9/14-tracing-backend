import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns):
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
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
async def test_TRC_116_service_map():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()
    t1 = uuid.uuid4().hex

    s1 = make_span(tenant, t1, "op1", "ingress-router", now, 10_000_000)
    s2 = make_span(tenant, t1, "op2", "order-backend", now, 20_000_000)

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s1, s2])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/services", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        assert "services" in data
        assert "ingress-router" in data["services"]
        assert "order-backend" in data["services"]
