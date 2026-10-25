"""
Mutual TLS (mTLS) client certificate verification and tenant identity extraction service.
Validates client certificate trust chain, validity periods, and extracts tenant identity from SAN or Subject CN.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509.oid import NameOID, ExtensionOID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import Tenant

class MtlsSecurityError(Exception):
    pass

class MtlsUntrustedCertError(MtlsSecurityError):
    pass

class MtlsExpiredCertError(MtlsSecurityError):
    pass

class MtlsTenantMappingError(MtlsSecurityError):
    pass

@dataclass(frozen=True)
class MtlsAuthContext:
    tenant_id: str
    subject_cn: str
    serial_number: str
    issuer: str
    san_uris: List[str]

class MtlsService:
    @staticmethod
    def parse_and_verify_cert(
        client_cert_pem: str,
        trusted_ca_pem: str,
        current_time: Optional[datetime] = None
    ) -> MtlsAuthContext:
        """
        Cryptographically verify that client_cert was issued by trusted_ca, is within its validity period,
        and extract the tenant identity.
        """
        now = current_time or datetime.now(timezone.utc)

        try:
            client_cert = x509.load_pem_x509_certificate(client_cert_pem.encode("utf-8"))
            ca_cert = x509.load_pem_x509_certificate(trusted_ca_pem.encode("utf-8"))
        except Exception as e:
            raise MtlsSecurityError(f"Failed to parse X.509 certificate: {e}")

        # 1. Validity period check
        if now < client_cert.not_valid_before_utc:
            raise MtlsExpiredCertError(f"Certificate not yet valid (valid from {client_cert.not_valid_before_utc})")
        if now > client_cert.not_valid_after_utc:
            raise MtlsExpiredCertError(f"Certificate expired at {client_cert.not_valid_after_utc}")

        # 2. Cryptographic signature check against CA public key
        ca_public_key = ca_cert.public_key()
        try:
            ca_public_key.verify(
                client_cert.signature,
                client_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                client_cert.signature_hash_algorithm
            )
        except Exception:
            raise MtlsUntrustedCertError("Client certificate signature does not match trusted CA")

        # 3. Subject CN extraction
        subject_cn = ""
        cn_attrs = client_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if cn_attrs:
            subject_cn = str(cn_attrs[0].value)

        # 4. SAN URI extraction (e.g. spiffe://tracing.dev/tenant/<tenant_id>)
        san_uris: List[str] = []
        try:
            san_ext = client_cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for uri in san_ext.value.get_values_for_type(x509.UniformResourceIdentifier):
                san_uris.append(str(uri))
        except x509.ExtensionNotFound:
            pass

        # 5. Determine tenant_id from SAN URI or Subject CN
        tenant_id = ""
        for uri in san_uris:
            if "tenant/" in uri:
                tenant_id = uri.split("tenant/")[-1].split("/")[0]
                break

        if not tenant_id and subject_cn:
            # Fallback to CN parsing (e.g. "tenant-abc.tracing.internal" or "tenant-abc")
            tenant_id = subject_cn.split(".")[0]

        if not tenant_id:
            raise MtlsTenantMappingError("Unable to extract tenant identity from client certificate SAN or CN")

        issuer_cn = ""
        ca_cn_attrs = ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if ca_cn_attrs:
            issuer_cn = str(ca_cn_attrs[0].value)

        return MtlsAuthContext(
            tenant_id=tenant_id,
            subject_cn=subject_cn,
            serial_number=hex(client_cert.serial_number),
            issuer=issuer_cn,
            san_uris=san_uris
        )

    @staticmethod
    async def authenticate_mtls(
        session: AsyncSession,
        client_cert_pem: str,
        trusted_ca_pem: str
    ) -> MtlsAuthContext:
        """
        Verify mTLS certificate and ensure extracted tenant exists and is active in PostgreSQL.
        """
        ctx = MtlsService.parse_and_verify_cert(client_cert_pem, trusted_ca_pem)

        stmt = select(Tenant).where(Tenant.id == ctx.tenant_id)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise MtlsTenantMappingError(f"Tenant '{ctx.tenant_id}' from client certificate does not exist")
        if tenant.status != "active":
            raise MtlsTenantMappingError(f"Tenant '{ctx.tenant_id}' is inactive")

        return ctx
