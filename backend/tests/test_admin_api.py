import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, start_ns):
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="test-svc",
        name="op",
        kind="SERVER",
        start_time_unix_nano=start_ns,
        end_time_unix_nano=start_ns + 10_000_000,
        duration_nanos=10_000_000,
        status_code="OK",
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_107_admin_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t_old = uuid.uuid4().hex
    t_new = uuid.uuid4().hex
    old_time = 1_000_000_000_000_000_000 # very old timestamp
    new_time = time.time_ns()

    spans = [
        make_span(tenant, t_old, old_time),
        make_span(tenant, t_new, new_time),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin stats
        resp_stats = await client.get("/api/v1/admin/stats", headers={"X-Tenant-ID": tenant})
        assert resp_stats.status_code == 200
        stats = resp_stats.json()
        assert stats["total_spans"] >= 2
        assert "storage" in stats

        # 2. Admin purge spans older than cutoff
        cutoff = old_time + 10_000_000_000
        purge_resp = await client.post(
            "/api/v1/admin/purge",
            json={"older_than_ns": cutoff},
            headers={"X-Tenant-ID": tenant}
        )
        assert purge_resp.status_code == 200
        purged_data = purge_resp.json()
        assert purged_data["purged_spans"] >= 1

        # 3. Verify old trace is gone, new trace remains
        get_old = await client.get(f"/api/v1/traces/{t_old}", headers={"X-Tenant-ID": tenant})
        assert get_old.status_code == 404
        get_new = await client.get(f"/api/v1/traces/{t_new}", headers={"X-Tenant-ID": tenant})
        assert get_new.status_code == 200
