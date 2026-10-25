import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from root_cause import RootCauseRanker

def test_TRC_141_root_cause_ranking_logic():
    # Spans in trace:
    # 1. Gateway (duration: 500ms, self-time: 50ms)
    # 2. Auth (duration: 30ms, self-time: 30ms, OK)
    # 3. Database (duration: 420ms, self-time: 420ms, on critical path, status: ERROR, baseline: 20ms) -> Obvious Root Cause!
    spans = [
        {
            "span_id": "s-gw",
            "parent_span_id": None,
            "service_name": "gateway",
            "name": "HTTP /order",
            "duration_nanos": 500_000_000,
            "status_code": "OK"
        },
        {
            "span_id": "s-auth",
            "parent_span_id": "s-gw",
            "service_name": "auth-service",
            "name": "verify_jwt",
            "duration_nanos": 30_000_000,
            "status_code": "OK"
        },
        {
            "span_id": "s-db",
            "parent_span_id": "s-gw",
            "service_name": "db-service",
            "name": "SELECT pg_locks",
            "duration_nanos": 420_000_000,
            "status_code": "ERROR",
            "events": [{"name": "exception", "exception.message": "deadlock detected"}]
        }
    ]

    ranked = RootCauseRanker.rank_root_causes(
        spans=spans,
        critical_path_ids={"s-gw", "s-db"},
        service_baselines_ms={"db-service": 20.0, "auth-service": 25.0}
    )

    assert len(ranked) == 3
    # Top ranked root cause must be s-db
    top = ranked[0]
    assert top["span_id"] == "s-db"
    assert top["service_name"] == "db-service"
    assert top["has_error"] is True
    assert top["is_critical_path"] is True
    assert top["root_cause_score"] > ranked[1]["root_cause_score"]
    assert len(top["reasons"]) >= 2

@pytest.mark.asyncio
async def test_TRC_141_root_cause_ranking_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "spans": [
                {
                    "span_id": "s-root",
                    "parent_span_id": None,
                    "service_name": "frontend",
                    "duration_nanos": 200_000_000,
                    "status_code": "OK"
                },
                {
                    "span_id": "s-culprit",
                    "parent_span_id": "s-root",
                    "service_name": "payment-api",
                    "duration_nanos": 190_000_000,
                    "status_code": "ERROR"
                }
            ],
            "critical_path_ids": ["s-root", "s-culprit"]
        }
        res = await client.post("/api/v1/ml/root-cause/rank", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 2
        assert data["ranked_candidates"][0]["span_id"] == "s-culprit"
        assert data["ranked_candidates"][0]["has_error"] is True
