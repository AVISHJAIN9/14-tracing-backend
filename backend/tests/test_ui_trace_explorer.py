import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns, status="OK"):
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
        status_code=status,
        attributes={"http.route": f"/api/{service}"}
    )

@pytest.mark.asyncio
async def test_TRC_112_trace_explorer():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()
    t1 = uuid.uuid4().hex
    t2 = uuid.uuid4().hex

    s1 = make_span(tenant, t1, "get_order", "order-svc", now, 20_000_000)
    s2 = make_span(tenant, t2, "charge_card", "pay-svc", now, 80_000_000, status="ERROR")

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s1, s2])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Explorer search all
        res_all = await client.get("/api/v1/traces/search", headers={"X-Tenant-ID": tenant})
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert len(data_all["traces"]) >= 2

        # 2. Explorer service filter
        res_svc = await client.get("/api/v1/traces/search?service=order-svc", headers={"X-Tenant-ID": tenant})
        assert res_svc.status_code == 200
        data_svc = res_svc.json()
        assert all(t["root_service_name"] == "order-svc" for t in data_svc["traces"])

        # 3. Explorer empty state
        res_none = await client.get("/api/v1/traces/search?service=nonexistent", headers={"X-Tenant-ID": tenant})
        assert res_none.status_code == 200
        assert len(res_none.json()["traces"]) == 0
