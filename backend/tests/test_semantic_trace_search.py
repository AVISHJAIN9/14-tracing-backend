import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from semantic_search import SemanticTraceSearchEngine

def test_TRC_145_semantic_trace_search_model():
    engine = SemanticTraceSearchEngine()

    traces = [
        {
            "trace_id": "t-sql-deadlock",
            "root_service_name": "checkout-service",
            "root_name": "POST /order",
            "duration_nanos": 450_000_000,
            "error_count": 1,
            "spans": [
                {"name": "POST /order", "service_name": "checkout", "status_code": "ERROR"},
                {"name": "UPDATE inventory", "service_name": "db", "status_code": "ERROR"}
            ]
        },
        {
            "trace_id": "t-jwt-validation",
            "root_service_name": "auth-service",
            "root_name": "GET /token",
            "duration_nanos": 15_000_000,
            "error_count": 0,
            "spans": [
                {"name": "verify_rsa_signature", "service_name": "auth", "status_code": "OK"}
            ]
        }
    ]

    # Query for database errors
    ranked_db = engine.rank_traces("database deadlock during inventory update", traces, top_k=2)
    assert len(ranked_db) == 2
    assert ranked_db[0]["trace_id"] == "t-sql-deadlock"
    assert ranked_db[0]["similarity_score"] > ranked_db[1]["similarity_score"]

    # Query for auth tokens
    ranked_auth = engine.rank_traces("verifying authentication token signature", traces, top_k=2)
    assert ranked_auth[0]["trace_id"] == "t-jwt-validation"
    assert ranked_auth[0]["similarity_score"] > ranked_auth[1]["similarity_score"]

@pytest.mark.asyncio
async def test_TRC_145_semantic_trace_search_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "query": "payment card gateway connection failure",
            "traces": [
                {
                    "trace_id": "t-payment-fail",
                    "root_service_name": "billing-service",
                    "root_name": "charge_credit_card",
                    "duration_nanos": 250_000_000,
                    "error_count": 1,
                    "spans": [{"name": "charge", "service_name": "stripe-client", "status_code": "ERROR"}]
                },
                {
                    "trace_id": "t-cache-hit",
                    "root_service_name": "catalog",
                    "root_name": "get_item",
                    "duration_nanos": 5_000_000,
                    "error_count": 0,
                    "spans": [{"name": "get", "service_name": "redis", "status_code": "OK"}]
                }
            ],
            "top_k": 2
        }
        res = await client.post("/api/v1/ml/semantic-search", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 2
        assert data["results"][0]["trace_id"] == "t-payment-fail"
