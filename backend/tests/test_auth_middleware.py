import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from security.tenant import TenantService
from security.api_key import ApiKeyService

@pytest.mark.asyncio
async def test_TRC_110_authentication_middleware():
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    raw_key = None
    async with get_db_session() as session:
        await TenantService.create_tenant(session, tenant_id, "Auth Middleware Tenant")
        raw_key, record = await ApiKeyService.create_api_key(
            session, tenant_id, name="Test Key", role="ingest"
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Public paths should succeed without credentials
        resp_health = await client.get("/healthz")
        assert resp_health.status_code == 200

        resp_ready = await client.get("/readyz")
        assert resp_ready.status_code == 200

        resp_metrics = await client.get("/metrics")
        assert resp_metrics.status_code == 200

        # 2. Protected endpoint with missing credentials -> 401 Unauthorized
        resp_no_auth = await client.get("/api/v1/auth/whoami")
        assert resp_no_auth.status_code == 401
        assert "WWW-Authenticate" in resp_no_auth.headers
        err = resp_no_auth.json()
        assert err["error"]["code"] == "UNAUTHORIZED"

        # 3. Protected endpoint with invalid/malformed API key -> 401
        resp_bad_auth = await client.get(
            "/api/v1/auth/whoami",
            headers={"Authorization": "Bearer invalid_key_format"}
        )
        assert resp_bad_auth.status_code == 401

        # 4. Protected endpoint with valid API key via Authorization header -> 200
        resp_auth = await client.get(
            "/api/v1/auth/whoami",
            headers={"Authorization": f"Bearer {raw_key}"}
        )
        assert resp_auth.status_code == 200
        body = resp_auth.json()
        assert body["tenant_id"] == tenant_id
        assert body["role"] == "ingest"

        # 5. Protected endpoint with valid API key via X-API-Key header -> 200
        resp_xkey = await client.get(
            "/api/v1/auth/whoami",
            headers={"X-API-Key": raw_key}
        )
        assert resp_xkey.status_code == 200
        assert resp_xkey.json()["tenant_id"] == tenant_id
