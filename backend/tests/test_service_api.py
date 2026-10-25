import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service):
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name=service,
        name=name,
        kind="SERVER",
        start_time_unix_nano=time.time_ns(),
        end_time_unix_nano=time.time_ns() + 10_000_000,
        duration_nanos=10_000_000,
        status_code="OK",
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_100_service_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t1 = uuid.uuid4().hex
    t2 = uuid.uuid4().hex

    spans = [
        make_span(tenant, t1, "get_user", "user-service"),
        make_span(tenant, t1, "update_user", "user-service"),
        make_span(tenant, t2, "charge", "payment-service"),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List services for tenant
        resp_svc = await client.get("/api/v1/services", headers={"X-Tenant-ID": tenant})
        assert resp_svc.status_code == 200
        services = resp_svc.json()["services"]
        assert "user-service" in services
        assert "payment-service" in services

        # 2. List operations for a specific service
        resp_ops = await client.get(
            "/api/v1/services/user-service/operations",
            headers={"X-Tenant-ID": tenant}
        )
        assert resp_ops.status_code == 200
        ops = resp_ops.json()["operations"]
        assert "get_user" in ops
        assert "update_user" in ops
        assert "charge" not in ops
