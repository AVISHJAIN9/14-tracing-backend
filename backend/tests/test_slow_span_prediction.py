import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from slow_span_predictor import SlowSpanPredictor

def test_TRC_148_slow_span_prediction_model():
    predictor = SlowSpanPredictor(random_state=42)

    # Generate 100 historical spans:
    # 60 fast spans (duration < 50ms, few attributes)
    # 40 slow spans (duration > 150ms, heavy attributes and events)
    spans = []
    for i in range(60):
        spans.append({
            "service_name": "fast-api",
            "name": "fast_handler",
            "kind": "SERVER",
            "duration_nanos": 25_000_000,
            "attributes": {"k": "v"},
            "events": [],
            "links": []
        })
    for i in range(40):
        spans.append({
            "service_name": "batch-cruncher",
            "name": "heavy_processing",
            "kind": "INTERNAL",
            "duration_nanos": 250_000_000,
            "attributes": {"k1": "v1", "k2": "v2", "k3": "v3", "k4": "v4", "k5": "v5"},
            "events": [{"name": "checkpoint_1"}, {"name": "checkpoint_2"}],
            "links": [{"trace_id": "t1", "span_id": "s1"}]
        })

    metrics = predictor.train_and_evaluate(spans, slow_threshold_ms=100.0, test_size=0.25)
    assert metrics["test_samples"] > 0
    assert metrics["accuracy"] >= 0.75

    # Predict probability for new unseen fast vs slow span
    prob_fast = predictor.predict_slow_probability({
        "service_name": "fast-api",
        "name": "fast_handler",
        "kind": "SERVER",
        "attributes": {},
        "events": [],
        "links": []
    })
    prob_slow = predictor.predict_slow_probability({
        "service_name": "batch-cruncher",
        "name": "heavy_processing",
        "kind": "INTERNAL",
        "attributes": {"heavy": True, "load": 100},
        "events": [{"name": "ev"}],
        "links": []
    })

    assert prob_slow > prob_fast

@pytest.mark.asyncio
async def test_TRC_148_slow_span_prediction_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Train
        train_spans = [
            {"service_name": "s1", "name": "op1", "duration_nanos": 20_000_000, "attributes": {}}
            for _ in range(30)
        ] + [
            {"service_name": "s2", "name": "op2", "duration_nanos": 300_000_000, "attributes": {"heavy": 1, "h2": 2}}
            for _ in range(20)
        ]

        train_res = await client.post(
            "/api/v1/ml/predictions/slow-spans/train",
            json={"spans": train_spans, "slow_threshold_ms": 100.0},
            headers={"X-Tenant-ID": "test-tenant"}
        )
        assert train_res.status_code == 200
        assert "metrics" in train_res.json()

        # Predict
        pred_res = await client.post(
            "/api/v1/ml/predictions/slow-spans/predict",
            json={"span": {"service_name": "s2", "name": "op2", "attributes": {"heavy": 1, "h2": 2}}},
            headers={"X-Tenant-ID": "test-tenant"}
        )
        assert pred_res.status_code == 200
        assert "slow_probability" in pred_res.json()
