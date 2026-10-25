import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

# Ensure ml is on path
project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from trace_anomaly import TraceAnomalyDetector

def test_TRC_138_trace_anomaly_detection_model():
    detector = TraceAnomalyDetector(contamination=0.05, random_state=42)

    # Generate 100 baseline traces with realistic variance (20-80ms, 5-11 spans, 0 errors)
    baseline_traces = [
        {
            "trace_id": f"t-norm-{i}",
            "duration_nanos": int((20 + (i % 20) * 3) * 1_000_000),
            "span_count": 5 + (i % 7),
            "max_depth": 2 + (i % 3),
            "error_count": 0,
            "max_fan_out": 2 + (i % 3)
        }
        for i in range(100)
    ]

    detector.fit(baseline_traces)

    # Test an obvious anomalous trace (5000ms, 80 spans, 5 errors, depth 15)
    anomalous_trace = {
        "trace_id": "t-anomaly-01",
        "duration_nanos": 5_000_000_000,
        "span_count": 80,
        "max_depth": 15,
        "error_count": 5,
        "max_fan_out": 12
    }

    normal_test_trace = {
        "trace_id": "t-normal-test",
        "duration_nanos": 55_000_000,
        "span_count": 8,
        "max_depth": 3,
        "error_count": 0,
        "max_fan_out": 2
    }

    preds = detector.predict([normal_test_trace, anomalous_trace])
    assert len(preds) == 2
    assert preds[0]["is_anomaly"] is False
    assert preds[1]["is_anomaly"] is True
    assert len(preds[1]["reasons"]) > 0

@pytest.mark.asyncio
async def test_TRC_138_trace_anomaly_detection_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "traces": [
                {
                    "trace_id": f"t-base-{i}",
                    "duration_nanos": 40_000_000,
                    "span_count": 5,
                    "max_depth": 2,
                    "error_count": 0,
                    "max_fan_out": 2
                }
                for i in range(20)
            ] + [
                {
                    "trace_id": "t-extreme-outlier",
                    "duration_nanos": 8_000_000_000,
                    "span_count": 200,
                    "max_depth": 25,
                    "error_count": 10,
                    "max_fan_out": 20
                }
            ]
        }
        res = await client.post("/api/v1/ml/anomalies/traces", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["anomaly_count"] >= 1
        outlier = next(r for r in data["results"] if r["trace_id"] == "t-extreme-outlier")
        assert outlier["is_anomaly"] is True
