"""
OAuth 2.0 / OpenID Connect (OIDC) integration service.
Handles OIDC discovery configuration, token claims normalization, tenant mapping,
and tenant provisioning/validation against PostgreSQL storage.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import Tenant

class OidcConfigError(Exception):
    pass

class OidcValidationError(Exception):
    pass

class OidcTenantMappingError(Exception):
    pass

@dataclass(frozen=True)
class OidcClaims:
    sub: str
    tenant_id: str
    roles: List[str]
    email: Optional[str]
    issuer: str
    audience: str
    extra_claims: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class OidcProviderConfig:
    issuer: str
    jwks_uri: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: Optional[str] = None

class OidcService:
    @staticmethod
    def parse_claims(
        raw_claims: Dict[str, Any],
        expected_issuer: str,
        expected_audience: str,
        tenant_claim_key: str = "tenant_id"
    ) -> OidcClaims:
        """
        Validate and normalize standard and custom OIDC claims.
        """
        if not raw_claims:
            raise OidcValidationError("Missing claims payload")

        iss = raw_claims.get("iss")
        if not iss or iss != expected_issuer:
            raise OidcValidationError(f"Invalid issuer: expected '{expected_issuer}', got '{iss}'")

        aud = raw_claims.get("aud")
        if isinstance(aud, list):
            if expected_audience not in aud:
                raise OidcValidationError(f"Expected audience '{expected_audience}' not found in aud list")
        elif aud != expected_audience:
            raise OidcValidationError(f"Invalid audience: expected '{expected_audience}', got '{aud}'")

        sub = raw_claims.get("sub")
        if not sub:
            raise OidcValidationError("OIDC claim missing mandatory 'sub'")

        # Tenant resolution from configured claim key (fallback to tenant claim or org_id)
        tenant_id = (
            raw_claims.get(tenant_claim_key)
            or raw_claims.get("org_id")
            or raw_claims.get("organization")
        )
        if not tenant_id:
            raise OidcTenantMappingError(f"No tenant mapping found in claim '{tenant_claim_key}'")

        # Roles extraction from roles / realm_access / resource_access
        roles: List[str] = []
        if "roles" in raw_claims and isinstance(raw_claims["roles"], list):
            roles.extend(raw_claims["roles"])
        elif "realm_access" in raw_claims and isinstance(raw_claims["realm_access"], dict):
            realm_roles = raw_claims["realm_access"].get("roles", [])
            if isinstance(realm_roles, list):
                roles.extend(realm_roles)

        if not roles:
            roles = ["readonly"]

        email = raw_claims.get("email")

        return OidcClaims(
            sub=sub,
            tenant_id=str(tenant_id),
            roles=roles,
            email=email,
            issuer=iss,
            audience=expected_audience,
            extra_claims=raw_claims
        )

    @staticmethod
    async def resolve_or_provision_tenant(
        session: AsyncSession,
        claims: OidcClaims,
        auto_provision: bool = False
    ) -> Tenant:
        """
        Resolve the tenant matching the OIDC claims from PostgreSQL.
        Optionally auto-provisions tenant if permitted.
        """
        stmt = select(Tenant).where(Tenant.id == claims.tenant_id)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            if auto_provision:
                tenant = Tenant(
                    id=claims.tenant_id,
                    name=f"Tenant {claims.tenant_id}",
                    status="active",
                    settings={"provisioned_via": "oidc", "oidc_issuer": claims.issuer}
                )
                session.add(tenant)
                await session.flush()
            else:
                raise OidcTenantMappingError(f"Tenant '{claims.tenant_id}' does not exist")

        if tenant.status != "active":
            raise OidcTenantMappingError(f"Tenant '{tenant.id}' is not active")

        return tenant
