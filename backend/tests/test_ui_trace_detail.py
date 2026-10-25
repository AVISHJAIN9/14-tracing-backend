import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, span_id, parent_id, name, service, start_ns, duration_ns, status="OK"):
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
        status_code=status,
        attributes={"http.method": "POST"}
    )

@pytest.mark.asyncio
async def test_TRC_113_trace_detail_page():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()
    trace_id = uuid.uuid4().hex
    root_id = uuid.uuid4().hex[:16]
    child_id = uuid.uuid4().hex[:16]

    s_root = make_span(tenant, trace_id, root_id, None, "checkout", "store-ui", now, 60_000_000)
    s_child = make_span(tenant, trace_id, child_id, root_id, "process_payment", "pay-svc", now + 10_000_000, 30_000_000)

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s_root, s_child])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch trace detail
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        detail = res.json()
        assert detail["trace_id"] == trace_id
        assert detail["span_count"] == 2
        assert detail["duration_nanos"] >= 40_000_000
        assert len(detail["spans"]) == 2

        # 2. Non-existent trace detail 404
        t_absent = uuid.uuid4().hex
        res_404 = await client.get(f"/api/v1/traces/{t_absent}", headers={"X-Tenant-ID": tenant})
        assert res_404.status_code == 404
