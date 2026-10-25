import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from performance_regression import PerformanceRegressionDetector

def test_TRC_147_performance_regression_logic():
    # Baseline: fast release (median ~20ms)
    baseline = [18.0, 19.5, 21.0, 20.2, 19.0, 22.1, 18.9, 20.5, 19.8, 20.0, 21.5, 19.2]
    # Canary: significant regression (median ~60ms)
    canary_regressed = [55.0, 58.2, 62.1, 60.0, 59.5, 64.0, 57.0, 61.2, 59.8, 63.0, 58.9, 62.5]
    # Canary: identical release (median ~20ms)
    canary_healthy = [18.5, 19.8, 20.8, 20.0, 19.2, 21.9, 19.1, 20.3, 19.9, 20.2, 21.1, 19.4]

    res_regressed = PerformanceRegressionDetector.detect_regression(baseline, canary_regressed)
    assert res_regressed["is_regression"] is True
    assert res_regressed["p_value"] < 0.001
    assert res_regressed["effect_size"] > 0.5
    assert res_regressed["median_delta_ms"] > 30.0

    res_healthy = PerformanceRegressionDetector.detect_regression(baseline, canary_healthy)
    assert res_healthy["is_regression"] is False
    assert res_healthy["p_value"] > 0.05

@pytest.mark.asyncio
async def test_TRC_147_performance_regression_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "baseline_durations_ms": [10.0, 11.0, 10.5, 11.2, 10.8, 11.5, 10.2],
            "canary_durations_ms": [35.0, 42.0, 38.5, 40.0, 37.2, 39.5, 41.0]
        }
        res = await client.post("/api/v1/ml/regressions/performance", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["is_regression"] is True
        assert data["p_value"] < 0.05
        assert data["median_delta_pct"] > 100.0
