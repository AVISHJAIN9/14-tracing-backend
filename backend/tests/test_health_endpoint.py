import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_104_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
