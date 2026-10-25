import time
import uuid
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from storage.db import get_db_session
from security.tenant import TenantService
from security.jwt_validator import (
    JwtValidator,
    JwtExpiredError,
    JwtSignatureError,
    JwtClaimsError,
    JwtSecurityError,
    JwtTenantError
)

SECRET_KEY = "my-super-secret-hmac-key-for-testing-12345678"
ISSUER = "https://auth.tracing.dev"
AUDIENCE = "tracing-collector"

@pytest.fixture(scope="module")
def rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")
    return private_pem, public_pem

def test_jwt_hs256_valid_verification():
    now = int(time.time())
    payload = {
        "sub": "user_456",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + 3600,
        "iat": now,
        "nbf": now,
        "tenant_id": "tenant-corp"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    verified = JwtValidator.decode_and_verify(token, SECRET_KEY, ISSUER, AUDIENCE, algorithms=["HS256"])
    assert verified["sub"] == "user_456"
    assert verified["tenant_id"] == "tenant-corp"

def test_jwt_rs256_asymmetric_verification(rsa_key_pair):
    private_pem, public_pem = rsa_key_pair
    now = int(time.time())
    payload = {
        "sub": "service_account_1",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + 1800,
        "iat": now,
        "nbf": now,
        "tenant_id": "tenant-enterprise"
    }
    token = jwt.encode(payload, private_pem, algorithm="RS256")
    verified = JwtValidator.decode_and_verify(token, public_pem, ISSUER, AUDIENCE, algorithms=["RS256"])
    assert verified["sub"] == "service_account_1"
    assert verified["tenant_id"] == "tenant-enterprise"

def test_jwt_expired_raises():
    now = int(time.time())
    payload = {
        "sub": "user_expired",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now - 30, # expired 30s ago
        "iat": now - 3600,
        "nbf": now - 3600,
        "tenant_id": "tenant-corp"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    with pytest.raises(JwtExpiredError, match="JWT token has expired"):
        JwtValidator.decode_and_verify(token, SECRET_KEY, ISSUER, AUDIENCE, algorithms=["HS256"], leeway=0)

def test_jwt_tampered_signature_raises():
    now = int(time.time())
    payload = {
        "sub": "user_tamper",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + 3600,
        "iat": now,
        "nbf": now,
        "tenant_id": "tenant-corp"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    tampered = token[:-4] + "abcd"
    with pytest.raises(JwtSignatureError):
        JwtValidator.decode_and_verify(tampered, SECRET_KEY, ISSUER, AUDIENCE, algorithms=["HS256"])

def test_jwt_banned_none_algorithm_rejected():
    payload = {
        "sub": "attacker",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "nbf": int(time.time()),
        "tenant_id": "tenant-corp"
    }
    # Unsigned token with alg=none
    none_token = jwt.encode(payload, key="", algorithm="none")
    with pytest.raises(JwtSecurityError, match="forbidden|insecure"):
        JwtValidator.decode_and_verify(none_token, SECRET_KEY, ISSUER, AUDIENCE, algorithms=["none"])

@pytest.mark.asyncio
async def test_jwt_validate_token_and_tenant():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    now = int(time.time())
    payload = {
        "sub": "user_tenant_test",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + 600,
        "iat": now,
        "nbf": now,
        "tenant_id": tid
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    async with get_db_session() as session:
        # Non-existent tenant raises
        with pytest.raises(JwtTenantError, match="does not exist"):
            await JwtValidator.validate_token_and_tenant(
                session, token, SECRET_KEY, ISSUER, AUDIENCE, algorithms=["HS256"]
            )

        # Create active tenant
        await TenantService.create_tenant(session, tid, "JWT Active Corp")

        # Now succeeds
        verified = await JwtValidator.validate_token_and_tenant(
            session, token, SECRET_KEY, ISSUER, AUDIENCE, algorithms=["HS256"]
        )
        assert verified["tenant_id"] == tid
