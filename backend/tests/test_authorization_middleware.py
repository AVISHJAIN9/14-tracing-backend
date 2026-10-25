import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from security.tenant import TenantService
from security.api_key import ApiKeyService

@pytest.mark.asyncio
async def test_TRC_111_authorization_middleware():
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    admin_key = None
    ingest_key = None
    readonly_key = None

    async with get_db_session() as session:
        await TenantService.create_tenant(session, tenant_id, "RBAC Tenant")
        admin_key, _ = await ApiKeyService.create_api_key(
            session, tenant_id, name="Admin Key", role="admin"
        )
        ingest_key, _ = await ApiKeyService.create_api_key(
            session, tenant_id, name="Ingest Key", role="ingest"
        )
        readonly_key, _ = await ApiKeyService.create_api_key(
            session, tenant_id, name="Readonly Key", role="readonly"
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin-only route: POST /api/v1/admin/purge
        # readonly role -> 403 Forbidden
        res_ro_admin = await client.post(
            "/api/v1/admin/purge",
            json={"older_than_ns": 1000},
            headers={"Authorization": f"Bearer {readonly_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_ro_admin.status_code == 403
        assert res_ro_admin.json()["error"]["code"] == "FORBIDDEN"

        # ingest role -> 403 Forbidden
        res_ing_admin = await client.post(
            "/api/v1/admin/purge",
            json={"older_than_ns": 1000},
            headers={"Authorization": f"Bearer {ingest_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_ing_admin.status_code == 403

        # admin role -> 200 OK
        res_adm_admin = await client.post(
            "/api/v1/admin/purge",
            json={"older_than_ns": 1000},
            headers={"Authorization": f"Bearer {admin_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_adm_admin.status_code == 200

        # 2. Ingest route: POST /api/v1/v1/traces
        # readonly role -> 403 Forbidden
        res_ro_ing = await client.post(
            "/api/v1/v1/traces",
            json={"resourceSpans": []},
            headers={"Authorization": f"Bearer {readonly_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_ro_ing.status_code == 403

        # ingest role -> 200 OK
        res_ing_ing = await client.post(
            "/api/v1/v1/traces",
            json={"resourceSpans": []},
            headers={"Authorization": f"Bearer {ingest_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_ing_ing.status_code == 200

        # 3. Query route: GET /api/v1/services
        # readonly role -> 200 OK
        res_ro_query = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {readonly_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_ro_query.status_code == 200

        # admin role -> 200 OK
        res_adm_query = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {admin_key}", "X-Tenant-ID": tenant_id}
        )
        assert res_adm_query.status_code == 200
