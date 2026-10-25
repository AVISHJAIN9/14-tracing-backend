import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from dynamic_sampling import DynamicSamplingOptimizer

def test_TRC_150_dynamic_sampling_optimization_logic():
    optimizer = DynamicSamplingOptimizer(
        target_spans_per_sec=1000.0,
        error_sampling_floor=1.0,
        slow_sampling_floor=1.0,
        min_routine_floor=0.05
    )

    registry = {}
    telemetry = [
        {"service": "analytics-collector", "spans_per_sec": 4000.0, "error_rate": 0.00, "p95_latency_ms": 10.0},
        {"service": "checkout-api", "spans_per_sec": 500.0, "error_rate": 0.12, "p95_latency_ms": 300.0}
    ]

    result = optimizer.optimize_and_apply(
        service_telemetry=telemetry,
        apply_to_registry=registry,
        tenant_id="test-tenant"
    )

    assert result["target_budget_spans_per_sec"] == 1000.0
    assert len(result["applied_updates"]) == 2
    assert result["total_audit_events"] >= 2
    assert result["floors_enforced"]["error_sampling_floor"] == 1.0

    # Ensure rule was applied to registry
    assert "test-tenant" in registry
    assert len(registry["test-tenant"]) == 2
    rule_map = {r["name"]: r for r in registry["test-tenant"]}
    assert "dyn_analytics-collector" in rule_map
    assert "dyn_checkout-api" in rule_map

    # Checkout API rate should be significantly higher due to errors and latency
    assert rule_map["dyn_checkout-api"]["sample_rate"] > rule_map["dyn_analytics-collector"]["sample_rate"]
    # Routine collector rate must respect minimum floor
    assert rule_map["dyn_analytics-collector"]["sample_rate"] >= 0.05

@pytest.mark.asyncio
async def test_TRC_150_dynamic_sampling_optimization_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "service_telemetry": [
                {"service": "web-frontend", "spans_per_sec": 2500.0, "error_rate": 0.02, "p95_latency_ms": 25.0},
                {"service": "billing-core", "spans_per_sec": 300.0, "error_rate": 0.20, "p95_latency_ms": 180.0}
            ],
            "target_spans_per_second": 1200.0
        }
        res = await client.post("/api/v1/ml/sampling/dynamic-optimize", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert len(data["applied_updates"]) == 2
        assert data["floors_enforced"]["error_sampling_floor"] == 1.0
