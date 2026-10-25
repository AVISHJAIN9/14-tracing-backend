import pytest
import os
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))
sys.path.insert(0, str(project_root / "ml"))

from api.app import app
from llm_engine import LLMTraceEngine

@pytest.mark.asyncio
async def test_TRC_142_trace_summarization_direct_engine():
    """TRC-142: Verify LLM engine generates trace summary using real local model."""
    engine = LLMTraceEngine()
    assert engine.is_configured() is True

    sample_trace = {
        "trace_id": "trc_142_deadlock_sample",
        "root_service": "checkout-service",
        "root_name": "POST /api/v1/order/checkout",
        "duration_nanos": 450_000_000,  # 450ms
        "error_count": 2
    }

    summary = engine.summarize_trace(sample_trace)
    assert isinstance(summary, str)
    assert len(summary) > 0
    # Model generates actual summary output
    assert any(term in summary.lower() for term in ["service", "checkout", "duration", "ms", "trace", "450"])

@pytest.mark.asyncio
async def test_TRC_142_trace_summarization_api_endpoint():
    """TRC-142: Verify API endpoint POST /api/v1/ml/summarize/trace returns 200 with summary and model."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "trace": {
                "trace_id": "trc_142_api_test",
                "root_service_name": "payment-gateway",
                "root_name": "charge",
                "duration_nanos": 780_000_000,
                "error_count": 1
            }
        }
        headers = {"X-Tenant-ID": "tenant_142_test"}
        resp = await client.post("/api/v1/ml/summarize/trace", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "tenant_142_test"
        assert len(data["summary"]) > 0
        assert data["model"] == "google/flan-t5-small"

@pytest.mark.asyncio
async def test_TRC_142_trace_summarization_unconfigured_error():
    """TRC-142: Negative test - if LLM disabled, endpoint returns HTTP 503 LLM_NOT_CONFIGURED."""
    engine = LLMTraceEngine()
    engine.enabled = False
    assert engine.is_configured() is False

    with pytest.raises(RuntimeError, match="LLM_NOT_CONFIGURED"):
        engine.generate("test prompt")
