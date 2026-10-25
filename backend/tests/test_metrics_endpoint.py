import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_106_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        content = resp.text
        # Verify Prometheus exposition format
        assert "trc_http_requests_total" in content
        assert "trc_ingested_spans_total" in content
        assert "trc_query_duration_seconds" in content
        assert "# TYPE" in content or "# HELP" in content
