import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_109_tenant_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = f"cust-{uuid.uuid4().hex[:8]}"

        # 1. Create Tenant
        payload = {
            "id": unique_id,
            "name": "Acme Aerospace",
            "settings": {"rate_limit": 500, "tier": "enterprise"}
        }
        res_post = await client.post("/api/v1/tenants", json=payload)
        assert res_post.status_code == 201
        data = res_post.json()
        assert data["id"] == unique_id
        assert data["name"] == "Acme Aerospace"
        assert data["status"] == "active"
        assert data["settings"]["rate_limit"] == 500

        # 2. Get Tenant
        res_get = await client.get(f"/api/v1/tenants/{unique_id}")
        assert res_get.status_code == 200
        got = res_get.json()
        assert got["id"] == unique_id
        assert got["name"] == "Acme Aerospace"

        # 3. List Tenants
        res_list = await client.get("/api/v1/tenants")
        assert res_list.status_code == 200
        tenants = res_list.json()
        assert any(t["id"] == unique_id for t in tenants)

        # 4. Update Tenant
        res_patch = await client.patch(
            f"/api/v1/tenants/{unique_id}",
            json={"status": "suspended", "settings": {"rate_limit": 0, "tier": "enterprise"}}
        )
        assert res_patch.status_code == 200
        updated = res_patch.json()
        assert updated["status"] == "suspended"
        assert updated["settings"]["rate_limit"] == 0

        # 5. Non-existent tenant lookup
        res_404 = await client.get("/api/v1/tenants/non-existent-tenant-999")
        assert res_404.status_code == 404

        # 6. Validation error: empty name or id
        res_bad = await client.post("/api/v1/tenants", json={"id": "", "name": ""})
        assert res_bad.status_code == 422
