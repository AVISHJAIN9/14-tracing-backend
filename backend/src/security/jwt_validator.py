"""
Cryptographic JWT validation service supporting asymmetric (RS256) and symmetric (HS256) keys.
Enforces expiration (exp), audience (aud), issuer (iss), algorithm allowlists, and tenant verification.
"""

from typing import Any, Dict, List, Optional
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import Tenant

class JwtSecurityError(Exception):
    pass

class JwtExpiredError(JwtSecurityError):
    pass

class JwtSignatureError(JwtSecurityError):
    pass

class JwtClaimsError(JwtSecurityError):
    pass

class JwtTenantError(JwtSecurityError):
    pass

class JwtValidator:
    BANNED_ALGORITHMS = {"none", "NONE", "None"}

    @staticmethod
    def decode_and_verify(
        token: str,
        secret_or_key: str,
        expected_issuer: str,
        expected_audience: str,
        algorithms: Optional[List[str]] = None,
        leeway: int = 10
    ) -> Dict[str, Any]:
        """
        Cryptographically verify signature and standard claims on a JWT.
        """
        if not token:
            raise JwtClaimsError("Missing JWT token string")

        allowed_algs = algorithms or ["RS256", "HS256"]
        for alg in allowed_algs:
            if alg in JwtValidator.BANNED_ALGORITHMS:
                raise JwtSecurityError(f"Insecure algorithm '{alg}' is forbidden")

        # Inspect unverified header to guard against 'none' algorithm bypass attacks
        try:
            unverified_header = jwt.get_unverified_header(token)
            alg_header = unverified_header.get("alg")
            if alg_header in JwtValidator.BANNED_ALGORITHMS or alg_header not in allowed_algs:
                raise JwtSecurityError(f"Unauthorized or insecure algorithm header: '{alg_header}'")
        except InvalidTokenError as e:
            raise JwtClaimsError(f"Malformed JWT header: {e}")

        try:
            payload = jwt.decode(
                token,
                key=secret_or_key,
                algorithms=allowed_algs,
                issuer=expected_issuer,
                audience=expected_audience,
                leeway=leeway,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["exp", "iss", "aud", "sub"]
                }
            )
            return payload
        except ExpiredSignatureError:
            raise JwtExpiredError("JWT token has expired")
        except (InvalidSignatureError, ImmatureSignatureError):
            raise JwtSignatureError("Invalid cryptographic signature or immature token")
        except (InvalidIssuerError, InvalidAudienceError) as e:
            raise JwtClaimsError(f"Claim verification failed: {e}")
        except InvalidTokenError as e:
            raise JwtClaimsError(f"Invalid token: {e}")

    @staticmethod
    async def validate_token_and_tenant(
        session: AsyncSession,
        token: str,
        secret_or_key: str,
        expected_issuer: str,
        expected_audience: str,
        tenant_claim_key: str = "tenant_id",
        algorithms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate cryptographic JWT signature/claims and ensure tenant exists and is active in PostgreSQL.
        """
        payload = JwtValidator.decode_and_verify(
            token=token,
            secret_or_key=secret_or_key,
            expected_issuer=expected_issuer,
            expected_audience=expected_audience,
            algorithms=algorithms
        )

        tenant_id = payload.get(tenant_claim_key)
        if not tenant_id:
            raise JwtTenantError(f"JWT payload missing tenant claim '{tenant_claim_key}'")

        stmt = select(Tenant).where(Tenant.id == str(tenant_id))
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise JwtTenantError(f"Tenant '{tenant_id}' does not exist")
        if tenant.status != "active":
            raise JwtTenantError(f"Tenant '{tenant_id}' is inactive")

        return payload
