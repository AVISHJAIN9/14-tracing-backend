import pytest
import os
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))
sys.path.insert(0, str(project_root / "ml"))

from api.app import app
from llm_engine import LLMTraceEngine, StructuredTraceQuery

@pytest.mark.asyncio
async def test_TRC_144_nl_query_translation_direct_engine():
    """TRC-144: Verify NL query translation produces valid structured JSON schema query object."""
    engine = LLMTraceEngine()
    assert engine.is_configured() is True

    nl_query = "Find failing requests in checkout-service taking over 500ms with database deadlock"
    structured = engine.parse_natural_language_query(nl_query)

    assert isinstance(structured, StructuredTraceQuery)
    assert structured.service == "checkout-service"
    assert structured.status == "ERROR"
    assert structured.min_duration_ms == 500.0
    assert "deadlock" in (structured.query_text or "")

@pytest.mark.asyncio
async def test_TRC_144_nl_query_never_raw_sql():
    """TRC-144: Invariant - NL queries must be translated to validated structured objects, never raw SQL."""
    engine = LLMTraceEngine()
    adversarial_query = "SELECT * FROM spans WHERE 1=1; DROP TABLE traces; --"
    structured = engine.parse_natural_language_query(adversarial_query)

    # Must be a validated Pydantic model with no SQL injection
    assert isinstance(structured, StructuredTraceQuery)
    dumped = structured.model_dump()
    assert "SELECT" not in str(dumped.get("service"))
    assert "DROP" not in str(dumped.get("service"))

@pytest.mark.asyncio
async def test_TRC_144_nl_query_api_endpoint():
    """TRC-144: Verify API endpoint POST /api/v1/ml/query/natural-language returns structured query object."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "query": "Show slow calls on auth-service under 200ms"
        }
        headers = {"X-Tenant-ID": "tenant_144_test"}
        resp = await client.post("/api/v1/ml/query/natural-language", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "tenant_144_test"
        assert "structured_query" in data
        sq = data["structured_query"]
        assert sq["service"] == "auth-service"
        assert sq["max_duration_ms"] == 200.0
        assert data["model"] == "google/flan-t5-small"
