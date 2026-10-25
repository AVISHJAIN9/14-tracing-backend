import pytest
import uuid
from storage.db import get_db_session
from security.tenant import TenantService
from security.api_key import (
    ApiKeyService,
    InvalidApiKeyError,
    RevokedApiKeyError,
    TenantInactiveError
)

@pytest.mark.asyncio
async def test_api_key_creation_and_hashing():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    async with get_db_session() as session:
        await TenantService.create_tenant(session, tid, "API Key Corp")
        raw_key, record = await ApiKeyService.create_api_key(
            session, tid, name="Ingestion Ingestion Agent", role="ingest"
        )
        assert raw_key.startswith("trc_live_")
        assert raw_key != record.key_hash
        assert record.key_hash.startswith("$argon2id$")
        assert record.role == "ingest"
        assert record.revoked_at is None

@pytest.mark.asyncio
async def test_api_key_successful_authentication():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    async with get_db_session() as session:
        await TenantService.create_tenant(session, tid, "Auth Corp")
        raw_key, record = await ApiKeyService.create_api_key(
            session, tid, name="CI Pipeline Key", role="admin"
        )

        auth_ctx = await ApiKeyService.authenticate_key(session, raw_key)
        assert auth_ctx.tenant_id == tid
        assert auth_ctx.key_id == record.id
        assert auth_ctx.role == "admin"
        assert auth_ctx.name == "CI Pipeline Key"

@pytest.mark.asyncio
async def test_api_key_invalid_and_tampered_fails():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    async with get_db_session() as session:
        await TenantService.create_tenant(session, tid, "Tamper Corp")
        raw_key, _ = await ApiKeyService.create_api_key(
            session, tid, name="Original Key"
        )

        # 1. Tampered payload
        tampered = raw_key[:-4] + "xxxx"
        with pytest.raises(InvalidApiKeyError):
            await ApiKeyService.authenticate_key(session, tampered)

        # 2. Completely unknown key
        with pytest.raises(InvalidApiKeyError):
            await ApiKeyService.authenticate_key(session, "trc_live_ffffffff_invalidsecretkey1234567890")

        # 3. Bad prefix format
        with pytest.raises(InvalidApiKeyError):
            await ApiKeyService.authenticate_key(session, "bad_key_without_prefix")

@pytest.mark.asyncio
async def test_api_key_revocation():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    async with get_db_session() as session:
        await TenantService.create_tenant(session, tid, "Revocation Corp")
        raw_key, record = await ApiKeyService.create_api_key(
            session, tid, name="Expiring Key"
        )

        # Active
        ctx = await ApiKeyService.authenticate_key(session, raw_key)
        assert ctx.key_id == record.id

        # Revoke
        revoked = await ApiKeyService.revoke_key(session, record.id)
        assert revoked is True

        # Now authentication must raise RevokedApiKeyError
        with pytest.raises(RevokedApiKeyError):
            await ApiKeyService.authenticate_key(session, raw_key)
