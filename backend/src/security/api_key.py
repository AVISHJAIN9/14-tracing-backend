"""
API key authentication service with Argon2id hashing, secure prefixing, and tenant binding.
API keys are displayed once upon generation and never stored in plaintext.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import ApiKey, Tenant

ph = PasswordHasher()

class InvalidApiKeyError(Exception):
    pass

class RevokedApiKeyError(Exception):
    pass

class TenantInactiveError(Exception):
    pass

@dataclass(frozen=True)
class ApiKeyAuthContext:
    tenant_id: str
    key_id: str
    role: str
    name: str

class ApiKeyService:
    KEY_PREFIX = "trc_live_"

    @staticmethod
    async def create_api_key(
        session: AsyncSession,
        tenant_id: str,
        name: str,
        role: str = "ingest"
    ) -> Tuple[str, ApiKey]:
        """
        Create a new API key. Returns (raw_key, api_key_record).
        Raw key is generated with CSPRNG and returned once; database only holds Argon2 hash.
        """
        prefix = secrets.token_hex(4) # 8-character prefix
        secret_part = secrets.token_urlsafe(32)
        raw_key = f"{ApiKeyService.KEY_PREFIX}{prefix}_{secret_part}"
        key_hash = ph.hash(raw_key)

        key_id = f"key_{secrets.token_hex(12)}"
        record = ApiKey(
            id=key_id,
            tenant_id=tenant_id,
            key_hash=key_hash,
            prefix=prefix,
            name=name,
            role=role,
            created_at=datetime.now(timezone.utc)
        )
        session.add(record)
        await session.flush()
        return raw_key, record

    @staticmethod
    async def authenticate_key(
        session: AsyncSession,
        raw_key: str
    ) -> ApiKeyAuthContext:
        """
        Authenticate an API key against database using Argon2id.
        """
        if not raw_key or not raw_key.startswith(ApiKeyService.KEY_PREFIX):
            raise InvalidApiKeyError("Malformed or missing API key format")

        payload = raw_key[len(ApiKeyService.KEY_PREFIX):]
        parts = payload.split("_", 1)
        if len(parts) != 2:
            raise InvalidApiKeyError("Malformed API key structure")
        prefix = parts[0]

        # Lookup candidate keys by prefix
        stmt = (
            select(ApiKey, Tenant)
            .join(Tenant, ApiKey.tenant_id == Tenant.id)
            .where(ApiKey.prefix == prefix)
        )
        result = await session.execute(stmt)
        candidates = result.all()

        if not candidates:
            raise InvalidApiKeyError("Invalid API key")

        for key_record, tenant_record in candidates:
            if key_record.revoked_at is not None:
                raise RevokedApiKeyError("API key has been revoked")

            if tenant_record.status != "active":
                raise TenantInactiveError(f"Tenant '{tenant_record.id}' is inactive")

            try:
                ph.verify(key_record.key_hash, raw_key)
                return ApiKeyAuthContext(
                    tenant_id=key_record.tenant_id,
                    key_id=key_record.id,
                    role=key_record.role,
                    name=key_record.name
                )
            except VerifyMismatchError:
                continue

        raise InvalidApiKeyError("Invalid API key")

    @staticmethod
    async def revoke_key(session: AsyncSession, key_id: str) -> bool:
        stmt = select(ApiKey).where(ApiKey.id == key_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return False
        record.revoked_at = datetime.now(timezone.utc)
        await session.flush()
        return True
