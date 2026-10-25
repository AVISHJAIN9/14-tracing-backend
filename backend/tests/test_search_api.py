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
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_099_search_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()

    t_payment = uuid.uuid4().hex
    t_auth = uuid.uuid4().hex

    spans = [
        make_span(tenant, t_payment, "charge_card", "billing-svc", now, 100_000_000, "OK"),
        make_span(tenant, t_auth, "verify_token", "auth-svc", now + 1_000_000_000, 20_000_000, "ERROR"),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Search all traces for tenant
        resp = await client.get("/api/v1/traces", headers={"X-Tenant-ID": tenant})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2

        # 2. Filter by service_name
        resp_svc = await client.get(
            "/api/v1/traces",
            params={"service_name": "billing-svc"},
            headers={"X-Tenant-ID": tenant}
        )
        assert resp_svc.status_code == 200
        results_svc = resp_svc.json()["results"]
        assert len(results_svc) == 1
        assert results_svc[0]["trace_id"] == t_payment

        # 3. Filter by status_code
        resp_status = await client.get(
            "/api/v1/traces",
            params={"status_code": "ERROR"},
            headers={"X-Tenant-ID": tenant}
        )
        assert resp_status.status_code == 200
        results_err = resp_status.json()["results"]
        assert len(results_err) == 1
        assert results_err[0]["trace_id"] == t_auth
