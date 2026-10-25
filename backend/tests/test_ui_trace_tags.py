import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_TRC_122_trace_tags_viewer():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    s1 = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="frontend-gw",
        name="render_page",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 50_000_000,
        duration_nanos=50_000_000,
        status_code="OK",
        attributes={"deployment.environment": "production", "service.tier": "edge"},
        events=[],
        links=[]
    )

    s2 = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="auth-service",
        name="check_session",
        kind="INTERNAL",
        start_time_unix_nano=now + 5_000_000,
        end_time_unix_nano=now + 25_000_000,
        duration_nanos=20_000_000,
        status_code="OK",
        attributes={"deployment.environment": "production", "auth.method": "jwt"},
        events=[],
        links=[]
    )

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s1, s2])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        spans = res.json()["spans"]

        # Aggregate unique tags across all spans
        all_tags = {}
        for s in spans:
            for k, v in s["attributes"].items():
                all_tags.setdefault(k, set()).add(str(v))

        assert "deployment.environment" in all_tags
        assert "production" in all_tags["deployment.environment"]
        assert "auth.method" in all_tags
        assert "service.tier" in all_tags
