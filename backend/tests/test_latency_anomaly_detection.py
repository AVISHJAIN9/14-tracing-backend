import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from latency_anomaly import LatencyAnomalyDetector

def test_TRC_139_latency_anomaly_model():
    detector = LatencyAnomalyDetector(threshold_mad=3.0)

    # 50 normal durations around 20ms (e.g. 18-22 ms)
    history = [20.0 + (i % 5) - 2.0 for i in range(50)]
    current = [21.0, 19.5, 120.0]  # 120ms is a clear latency spike outlier

    detections = detector.detect_latency_anomalies(
        service="checkout-service",
        operation="process_payment",
        history_durations_ms=history,
        current_durations_ms=current
    )

    assert len(detections) == 3
    assert detections[0]["is_anomaly"] is False
    assert detections[1]["is_anomaly"] is False
    assert detections[2]["is_anomaly"] is True
    assert detections[2]["modified_z_score"] > 3.0

@pytest.mark.asyncio
async def test_TRC_139_latency_anomaly_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "service": "order-api",
            "operation": "get_order",
            "history_durations_ms": [15.0, 16.0, 14.5, 15.5, 15.0, 16.2, 14.8, 15.1, 15.3, 14.9],
            "current_durations_ms": [15.2, 85.0],
            "threshold_mad": 3.0
        }
        res = await client.post("/api/v1/ml/anomalies/latency", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["anomaly_count"] == 1
        assert data["anomalies"][0]["duration_ms"] == 85.0
        assert data["anomalies"][0]["is_anomaly"] is True
