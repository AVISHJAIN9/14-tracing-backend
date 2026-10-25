import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_105_readiness_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Healthy database ready check
        resp = await client.get("/readyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["dependencies"]["postgres"] == "ok"
