import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from sampling_recommendation import SamplingRecommender

def test_TRC_149_sampling_recommendation_logic():
    telemetry = [
        # Heavy volume service with 0% error rate
        {"service": "static-assets", "spans_per_sec": 5000.0, "error_rate": 0.00, "p95_latency_ms": 5.0},
        # High error, critical billing service
        {"service": "payment-api", "spans_per_sec": 200.0, "error_rate": 0.15, "p95_latency_ms": 250.0},
        # Normal service
        {"service": "user-service", "spans_per_sec": 800.0, "error_rate": 0.01, "p95_latency_ms": 35.0}
    ]

    recs = SamplingRecommender.recommend_sampling_policies(
        service_telemetry=telemetry,
        target_spans_per_second=1000.0
    )

    assert len(recs["recommended_policies"]) == 3
    pol_map = {p["service"]: p for p in recs["recommended_policies"]}

    # Payment API should have higher sample rate than routine static assets
    assert pol_map["payment-api"]["recommended_sample_rate"] > pol_map["static-assets"]["recommended_sample_rate"]
    assert "100% error spans retained" in pol_map["payment-api"]["guaranteed_rules"]

@pytest.mark.asyncio
async def test_TRC_149_sampling_recommendation_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "service_telemetry": [
                {"service": "api-gw", "spans_per_sec": 3000.0, "error_rate": 0.01, "p95_latency_ms": 20.0},
                {"service": "auth", "spans_per_sec": 500.0, "error_rate": 0.08, "p95_latency_ms": 80.0}
            ],
            "target_spans_per_second": 1500.0
        }
        res = await client.post("/api/v1/ml/sampling/recommendations", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert len(data["recommended_policies"]) == 2
        assert "within_budget" in data
