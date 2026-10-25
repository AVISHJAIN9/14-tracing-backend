import pytest
import uuid
from storage.db import get_db_session
from security.tenant import TenantService
from security.oidc import (
    OidcService,
    OidcClaims,
    OidcValidationError,
    OidcTenantMappingError
)

def test_oidc_claims_parsing():
    raw = {
        "iss": "https://auth.example.com",
        "aud": "tracing-backend-api",
        "sub": "user_12345678",
        "tenant_id": "tenant-enterprise",
        "email": "alice@example.com",
        "realm_access": {"roles": ["admin", "query"]}
    }

    claims = OidcService.parse_claims(
        raw_claims=raw,
        expected_issuer="https://auth.example.com",
        expected_audience="tracing-backend-api"
    )

    assert claims.sub == "user_12345678"
    assert claims.tenant_id == "tenant-enterprise"
    assert claims.roles == ["admin", "query"]
    assert claims.email == "alice@example.com"

def test_oidc_claims_validation_failures():
    raw = {
        "iss": "https://rogue-auth.example.com",
        "aud": "tracing-backend-api",
        "sub": "user_123",
        "tenant_id": "tenant-enterprise"
    }
    with pytest.raises(OidcValidationError, match="Invalid issuer"):
        OidcService.parse_claims(raw, "https://auth.example.com", "tracing-backend-api")

    raw_bad_aud = {
        "iss": "https://auth.example.com",
        "aud": "other-service",
        "sub": "user_123",
        "tenant_id": "tenant-enterprise"
    }
    with pytest.raises(OidcValidationError, match="Invalid audience"):
        OidcService.parse_claims(raw_bad_aud, "https://auth.example.com", "tracing-backend-api")

    raw_missing_tenant = {
        "iss": "https://auth.example.com",
        "aud": "tracing-backend-api",
        "sub": "user_123"
    }
    with pytest.raises(OidcTenantMappingError, match="No tenant mapping found"):
        OidcService.parse_claims(raw_missing_tenant, "https://auth.example.com", "tracing-backend-api")

@pytest.mark.asyncio
async def test_oidc_tenant_resolution_and_provisioning():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    claims = OidcClaims(
        sub="sub_abc",
        tenant_id=tid,
        roles=["query"],
        email="test@example.com",
        issuer="https://auth.example.com",
        audience="tracing-backend-api"
    )

    async with get_db_session() as session:
        # 1. Non-existent without auto-provision raises
        with pytest.raises(OidcTenantMappingError, match="does not exist"):
            await OidcService.resolve_or_provision_tenant(session, claims, auto_provision=False)

        # 2. Auto-provision creates new tenant record
        provisioned = await OidcService.resolve_or_provision_tenant(session, claims, auto_provision=True)
        assert provisioned.id == tid
        assert provisioned.status == "active"
        assert provisioned.settings.get("provisioned_via") == "oidc"

        # 3. Existing active tenant resolves successfully
        resolved = await OidcService.resolve_or_provision_tenant(session, claims, auto_provision=False)
        assert resolved.id == tid
