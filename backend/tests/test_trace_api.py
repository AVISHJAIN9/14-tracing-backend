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
        attributes={"http.status_code": "200"}
    )

@pytest.mark.asyncio
async def test_TRC_098_trace_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    span = make_span(tenant, trace_id, "root_op", "api-gw", now, 25_000_000)

    async with get_db_session(tenant_id=tenant) as session:
        session.add(span)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch trace with valid tenant header
        resp = await client.get(
            f"/api/v1/traces/{trace_id}",
            headers={"X-Tenant-ID": tenant}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trace_id"] == trace_id
        assert data["total_spans"] == 1
        assert len(data["spans"]) == 1
        assert data["spans"][0]["name"] == "root_op"

        # 2. Non-existent trace returns 404
        non_existent = uuid.uuid4().hex
        resp_404 = await client.get(
            f"/api/v1/traces/{non_existent}",
            headers={"X-Tenant-ID": tenant}
        )
        assert resp_404.status_code == 404

        # 3. Cross-tenant access: other tenant cannot read this trace (404 / 403)
        other_tenant = f"tenant-other-{uuid.uuid4().hex[:6]}"
        resp_other = await client.get(
            f"/api/v1/traces/{trace_id}",
            headers={"X-Tenant-ID": other_tenant}
        )
        assert resp_other.status_code == 404
