import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from error_spike import ErrorSpikeDetector

def test_TRC_140_error_spike_model():
    detector = ErrorSpikeDetector(drift_k=0.1, threshold_h=4.0)

    # Low baseline error counts: 0 or 1 error per interval
    baseline = [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0]

    # Recent counts experience severe spike (10, 12, 15 errors)
    recent_spiking = [0, 1, 8, 12, 15]
    recent_calm = [0, 0, 1, 0, 0]

    res_spike = detector.detect_error_spike(
        service="user-auth-service",
        baseline_error_counts=baseline,
        recent_error_counts=recent_spiking
    )
    assert res_spike["is_error_spike"] is True
    assert res_spike["cusum_statistic"] >= 4.0
    assert res_spike["change_point_index"] >= 0
    assert res_spike["poisson_p_value"] < 0.01

    res_calm = detector.detect_error_spike(
        service="user-auth-service",
        baseline_error_counts=baseline,
        recent_error_counts=recent_calm
    )
    assert res_calm["is_error_spike"] is False

@pytest.mark.asyncio
async def test_TRC_140_error_spike_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "service": "billing-api",
            "baseline_error_counts": [0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
            "recent_error_counts": [0, 2, 8, 14, 20]
        }
        res = await client.post("/api/v1/ml/anomalies/error-spikes", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "billing-api"
        assert data["is_error_spike"] is True
        assert data["cusum_statistic"] > 5.0
