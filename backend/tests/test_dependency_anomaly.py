import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

project_root = Path(__file__).resolve().parent.parent.parent
ml_path = str(project_root / "ml")
if ml_path not in sys.path:
    sys.path.insert(0, ml_path)

from dependency_anomaly import DependencyAnomalyDetector

def test_TRC_146_dependency_anomaly_logic():
    baseline_edges = [
        {"caller": "gateway", "callee": "auth", "latency_ms": 10.0, "call_count": 1000},
        {"caller": "gateway", "callee": "orders", "latency_ms": 25.0, "call_count": 800},
        {"caller": "orders", "callee": "inventory", "latency_ms": 15.0, "call_count": 800}
    ]

    current_edges = [
        # auth latency regression: 10ms -> 30ms (3.0x)
        {"caller": "gateway", "callee": "auth", "latency_ms": 30.0, "call_count": 1000},
        # orders volume surge: 800 -> 2500 calls (3.1x)
        {"caller": "gateway", "callee": "orders", "latency_ms": 26.0, "call_count": 2500},
        # new unheralded dependency edge
        {"caller": "gateway", "callee": "unauthorized-db", "latency_ms": 50.0, "call_count": 100}
        # missing: orders -> inventory dropped
    ]

    anomalies = DependencyAnomalyDetector.detect_dependency_anomalies(
        baseline_edges=baseline_edges,
        current_edges=current_edges
    )

    types = {a["anomaly_type"] for a in anomalies}
    assert "LATENCY_REGRESSION" in types
    assert "TRAFFIC_VOLUME_SURGE" in types
    assert "NEW_DEPENDENCY_EDGE" in types
    assert "MISSING_DEPENDENCY_EDGE" in types

@pytest.mark.asyncio
async def test_TRC_146_dependency_anomaly_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "baseline_edges": [{"caller": "api", "callee": "cache", "latency_ms": 2.0, "call_count": 500}],
            "current_edges": [{"caller": "api", "callee": "cache", "latency_ms": 10.0, "call_count": 500}]
        }
        res = await client.post("/api/v1/ml/anomalies/dependencies", json=payload, headers={"X-Tenant-ID": "test-tenant"})
        assert res.status_code == 200
        data = res.json()
        assert data["count"] >= 1
        assert data["anomalies"][0]["anomaly_type"] == "LATENCY_REGRESSION"
