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
async def test_TRC_143_incident_summarization_direct_engine():
    """TRC-143: Verify LLM engine synthesizes multi-trace incident report with real model."""
    engine = LLMTraceEngine()
    assert engine.is_configured() is True

    traces = [
        {
            "trace_id": "trc_143_inc_1",
            "root_service": "auth-service",
            "root_name": "verify_token",
            "duration_nanos": 920_000_000,
            "error_count": 1
        },
        {
            "trace_id": "trc_143_inc_2",
            "root_service": "api-gateway",
            "root_name": "route_request",
            "duration_nanos": 1_200_000_000,
            "error_count": 1
        }
    ]

    summary = engine.summarize_incident(traces, "Auth Service Outage")
    assert isinstance(summary, str)
    assert len(summary) > 0

@pytest.mark.asyncio
async def test_TRC_143_incident_summarization_empty_traces():
    """TRC-143: Verify handling of empty traces list."""
    engine = LLMTraceEngine()
    res = engine.summarize_incident([], "Empty Incident")
    assert "No traces" in res

@pytest.mark.asyncio
async def test_TRC_143_incident_summarization_api_endpoint():
    """TRC-143: Verify API endpoint POST /api/v1/ml/summarize/incident returns 200 with model name."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "incident_title": "Database Connection Exhaustion",
            "traces": [
                {
                    "trace_id": "trc_143_db_1",
                    "root_service": "inventory-service",
                    "root_name": "reserve_stock",
                    "duration_nanos": 2_500_000_000,
                    "error_count": 3
                }
            ]
        }
        headers = {"X-Tenant-ID": "tenant_143_test"}
        resp = await client.post("/api/v1/ml/summarize/incident", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "tenant_143_test"
        assert len(data["summary"]) > 0
        assert data["model"] == "google/flan-t5-small"
