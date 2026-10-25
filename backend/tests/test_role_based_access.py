import pytest
import uuid
from storage.db import get_db_session
from security.tenant import TenantService
from security.api_key import ApiKeyService
from security.rbac import (
    RbacService,
    Permission,
    Role,
    AccessDeniedError
)

def test_rbac_matrix_permissions():
    # Ingest role
    assert RbacService.has_permission(["ingest"], Permission.INGEST_SPANS) is True
    assert RbacService.has_permission(["ingest"], Permission.QUERY_SPANS) is False
    assert RbacService.has_permission(["ingest"], Permission.MANAGE_API_KEYS) is False

    # Query role
    assert RbacService.has_permission(["query"], Permission.QUERY_SPANS) is True
    assert RbacService.has_permission(["query"], Permission.QUERY_TRACES) is True
    assert RbacService.has_permission(["query"], Permission.INGEST_SPANS) is False

    # Admin role
    for perm in Permission:
        assert RbacService.has_permission(["admin"], perm) is True

    # Readonly role
    assert RbacService.has_permission(["readonly"], Permission.QUERY_SPANS) is True
    assert RbacService.has_permission(["readonly"], Permission.DELETE_SPANS) is False

def test_rbac_deny_by_default():
    assert RbacService.has_permission([], Permission.QUERY_SPANS) is False
    assert RbacService.has_permission(["unknown_role"], Permission.QUERY_SPANS) is False

    with pytest.raises(AccessDeniedError, match="Access denied: permission 'spans:delete'"):
        RbacService.enforce_permission(["query"], Permission.DELETE_SPANS)

@pytest.mark.asyncio
async def test_rbac_integration_with_db_api_key():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    async with get_db_session() as session:
        await TenantService.create_tenant(session, tid, "RBAC Corp")
        
        # 1. Create Ingestion-only API key
        raw_key, _ = await ApiKeyService.create_api_key(
            session, tid, name="Ingest Bot", role="ingest"
        )
        auth_ctx = await ApiKeyService.authenticate_key(session, raw_key)
        
        # Should succeed for ingest
        RbacService.enforce_permission([auth_ctx.role], Permission.INGEST_SPANS)
        
        # Should be denied for query
        with pytest.raises(AccessDeniedError, match="spans:query"):
            RbacService.enforce_permission([auth_ctx.role], Permission.QUERY_SPANS)

        # 2. Create Admin API key
        raw_admin, _ = await ApiKeyService.create_api_key(
            session, tid, name="Admin Key", role="admin"
        )
        admin_ctx = await ApiKeyService.authenticate_key(session, raw_admin)
        RbacService.enforce_permission([admin_ctx.role], Permission.MANAGE_API_KEYS)
        RbacService.enforce_permission([admin_ctx.role], Permission.QUERY_SPANS)
