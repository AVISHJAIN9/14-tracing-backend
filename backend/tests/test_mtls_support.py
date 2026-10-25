import datetime
from datetime import timezone
import uuid
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from storage.db import get_db_session
from security.tenant import TenantService
from security.mtls import (
    MtlsService,
    MtlsUntrustedCertError,
    MtlsExpiredCertError,
    MtlsTenantMappingError
)

def build_ca():
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Tracing Trust CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Tracing Root CA")
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    ca_cert_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return ca_key, ca_cert_pem

def issue_client_cert(
    ca_key,
    ca_cert_pem,
    common_name: str,
    san_uri: str = None,
    valid_days: int = 30,
    start_offset_days: int = 0
):
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode("utf-8"))
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name)
    ])
    now = datetime.datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now + datetime.timedelta(days=start_offset_days))
        .not_valid_after(now + datetime.timedelta(days=start_offset_days + valid_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )
    if san_uri:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(san_uri)]),
            critical=False
        )
    client_cert = builder.sign(ca_key, hashes.SHA256())
    client_cert_pem = client_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return client_cert_pem

@pytest.fixture(scope="module")
def pki_setup():
    ca_key, ca_cert_pem = build_ca()
    rogue_key, rogue_ca_pem = build_ca()
    return ca_key, ca_cert_pem, rogue_key, rogue_ca_pem

def test_mtls_valid_cert_verification(pki_setup):
    ca_key, ca_cert_pem, _, _ = pki_setup
    san = "spiffe://tracing.dev/tenant/tenant-corp-prod"
    client_pem = issue_client_cert(ca_key, ca_cert_pem, common_name="agent-01", san_uri=san)

    ctx = MtlsService.parse_and_verify_cert(client_pem, ca_cert_pem)
    assert ctx.tenant_id == "tenant-corp-prod"
    assert ctx.subject_cn == "agent-01"
    assert ctx.issuer == "Tracing Root CA"
    assert san in ctx.san_uris

def test_mtls_untrusted_ca_fails(pki_setup):
    ca_key, ca_cert_pem, rogue_key, rogue_ca_pem = pki_setup
    # Issued by rogue CA
    rogue_client_pem = issue_client_cert(rogue_key, rogue_ca_pem, common_name="intruder")

    # Verifying against trusted CA must fail
    with pytest.raises(MtlsUntrustedCertError, match="does not match trusted CA"):
        MtlsService.parse_and_verify_cert(rogue_client_pem, ca_cert_pem)

def test_mtls_expired_cert_fails(pki_setup):
    ca_key, ca_cert_pem, _, _ = pki_setup
    # Expired 10 days ago
    expired_pem = issue_client_cert(
        ca_key, ca_cert_pem, common_name="old-agent", valid_days=5, start_offset_days=-20
    )

    with pytest.raises(MtlsExpiredCertError, match="Certificate expired"):
        MtlsService.parse_and_verify_cert(expired_pem, ca_cert_pem)

@pytest.mark.asyncio
async def test_mtls_authenticate_with_postgres_tenant(pki_setup):
    ca_key, ca_cert_pem, _, _ = pki_setup
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    client_pem = issue_client_cert(
        ca_key, ca_cert_pem, common_name=f"{tid}.tracing.internal"
    )

    async with get_db_session() as session:
        # Fails before tenant exists in PostgreSQL
        with pytest.raises(MtlsTenantMappingError, match="does not exist"):
            await MtlsService.authenticate_mtls(session, client_pem, ca_cert_pem)

        # Create active tenant
        await TenantService.create_tenant(session, tid, "mTLS Enterprise")

        # Now authentication succeeds
        ctx = await MtlsService.authenticate_mtls(session, client_pem, ca_cert_pem)
        assert ctx.tenant_id == tid
