import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord
from query.critical_path import CriticalPathAnalyzer

def test_TRC_124_critical_path_pure_logic():
    now = time.time_ns()
    # Tree:
    # root (duration: 100ms)
    #  ├── child1 (duration: 30ms) -> grandchild1 (duration: 10ms) [Total branch: 40ms]
    #  └── child2 (duration: 80ms) -> grandchild2 (duration: 50ms) [Total branch: 130ms] -> Bottleneck/Critical Path
    root = {
        "span_id": "s-root",
        "parent_span_id": None,
        "service_name": "gateway",
        "name": "HTTP GET /checkout",
        "start_time_unix_nano": now,
        "end_time_unix_nano": now + 100_000_000,
        "duration_nanos": 100_000_000
    }
    child1 = {
        "span_id": "s-c1",
        "parent_span_id": "s-root",
        "service_name": "user-svc",
        "name": "get_profile",
        "start_time_unix_nano": now + 5_000_000,
        "end_time_unix_nano": now + 35_000_000,
        "duration_nanos": 30_000_000
    }
    child2 = {
        "span_id": "s-c2",
        "parent_span_id": "s-root",
        "service_name": "inventory-svc",
        "name": "reserve_items",
        "start_time_unix_nano": now + 10_000_000,
        "end_time_unix_nano": now + 90_000_000,
        "duration_nanos": 80_000_000
    }
    gc2 = {
        "span_id": "s-gc2",
        "parent_span_id": "s-c2",
        "service_name": "db",
        "name": "UPDATE inventory",
        "start_time_unix_nano": now + 15_000_000,
        "end_time_unix_nano": now + 65_000_000,
        "duration_nanos": 50_000_000
    }

    res = CriticalPathAnalyzer.compute_critical_path([root, child1, child2, gc2])
    assert "s-root" in res["critical_path_span_ids"]
    assert "s-c2" in res["critical_path_span_ids"]
    assert "s-gc2" in res["critical_path_span_ids"]
    assert "s-c1" not in res["critical_path_span_ids"]
    assert res["critical_path_duration_nanos"] > 0

@pytest.mark.asyncio
async def test_TRC_124_critical_path_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    root_id = uuid.uuid4().hex[:16]
    child_id = uuid.uuid4().hex[:16]
    now = time.time_ns()

    s_root = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=root_id,
        parent_span_id=None,
        service_name="api-gateway",
        name="dispatch",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 50_000_000,
        duration_nanos=50_000_000,
        status_code="OK",
        attributes={},
        events=[],
        links=[]
    )
    s_child = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=child_id,
        parent_span_id=root_id,
        service_name="billing-worker",
        name="charge_card",
        kind="CLIENT",
        start_time_unix_nano=now + 5_000_000,
        end_time_unix_nano=now + 45_000_000,
        duration_nanos=40_000_000,
        status_code="OK",
        attributes={},
        events=[],
        links=[]
    )

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([s_root, s_child])
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}/critical-path", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        assert data["trace_id"] == trace_id
        assert root_id in data["critical_path_span_ids"]
        assert child_id in data["critical_path_span_ids"]
        assert len(data["segments"]) == 2
