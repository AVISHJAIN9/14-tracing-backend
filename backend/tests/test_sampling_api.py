import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_102_sampling_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get initial sampling rules
        resp = await client.get("/api/v1/sampling/rules", headers={"X-Tenant-ID": tenant})
        assert resp.status_code == 200
        data = resp.json()
        assert "rules" in data

        # 2. Create new sampling rule
        rule_payload = {
            "name": "high_value_checkout",
            "service_pattern": "checkout-.*",
            "route_pattern": "/pay/.*",
            "sample_rate": 1.0
        }
        post_resp = await client.post(
            "/api/v1/sampling/rules",
            json=rule_payload,
            headers={"X-Tenant-ID": tenant}
        )
        assert post_resp.status_code == 201
        created = post_resp.json()
        assert created["name"] == "high_value_checkout"
        assert created["sample_rate"] == 1.0

        # 3. Retrieve rules again and confirm new rule is listed
        get_resp = await client.get("/api/v1/sampling/rules", headers={"X-Tenant-ID": tenant})
        assert get_resp.status_code == 200
        rules = get_resp.json()["rules"]
        assert any(r["name"] == "high_value_checkout" for r in rules)
