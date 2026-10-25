import pytest
import uuid
from sqlalchemy import text
from storage.db import get_db_session
from storage.models import SpanRecord
from security.header_redaction import HeaderRedactor

def test_header_redaction_direct_map():
    redactor = HeaderRedactor()
    headers = {
        "Host": "api.tracing.io",
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsIn...",
        "Cookie": "session_id=s3cr3t_c00k13; secure=true",
        "X-Api-Key": "secret_agent_key_999",
        "X-Custom-Tracking": "track-12345"
    }

    cleaned = redactor.redact_headers_dict(headers)

    assert cleaned["Authorization"] == "[REDACTED]"
    assert cleaned["Cookie"] == "[REDACTED]"
    assert cleaned["X-Api-Key"] == "[REDACTED]"

    assert cleaned["Host"] == "api.tracing.io"
    assert cleaned["Content-Type"] == "application/json"
    assert cleaned["X-Custom-Tracking"] == "track-12345"

def test_header_redaction_otel_attributes():
    redactor = HeaderRedactor()
    attributes = {
        "http.method": "GET",
        "http.route": "/v1/account",
        "http.request.header.authorization": "Basic dXNlcjpwYXNz",
        "http.request.header.cookie": "auth_token=abc123xyz",
        "http.request.header.user-agent": "Mozilla/5.0",
        "http.response.header.set-cookie": "remember_me=bad_secret",
        "http.response.header.content-length": "1024"
    }

    cleaned = redactor.redact_span_attributes(attributes)

    assert cleaned["http.request.header.authorization"] == "[REDACTED]"
    assert cleaned["http.request.header.cookie"] == "[REDACTED]"
    assert cleaned["http.response.header.set-cookie"] == "[REDACTED]"

    assert cleaned["http.method"] == "GET"
    assert cleaned["http.request.header.user-agent"] == "Mozilla/5.0"
    assert cleaned["http.response.header.content-length"] == "1024"

@pytest.mark.asyncio
async def test_header_redaction_persisted_to_postgres():
    """
    Assert invariant: sensitive headers captured in span attributes are masked
    before storage in PostgreSQL, proven by querying raw tables.
    """
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]

    redactor = HeaderRedactor()
    raw_attributes = {
        "service.name": "ingress-gateway",
        "http.request.header.authorization": "Bearer TopSecretTokenValue123456",
        "http.request.header.cookie": "session_id=PlaintextSessionCookie987654",
        "http.request.header.accept": "application/json"
    }

    sanitized = redactor.redact_span_attributes(raw_attributes)

    async with get_db_session(tenant_id=tid) as session:
        span = SpanRecord(
            tenant_id=tid,
            trace_id=trace_id,
            span_id=span_id,
            name="HandleHttpRequest",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000050000000,
            duration_nanos=50000000,
            status_code="OK",
            attributes=sanitized,
            events=[],
            links=[],
            service_name="ingress-gateway"
        )
        session.add(span)

    # Inspect raw table in PostgreSQL
    async with get_db_session(tenant_id=tid) as session:
        result = await session.execute(
            text(f"SELECT attributes FROM spans WHERE tenant_id = '{tid}' AND span_id = '{span_id}'")
        )
        stored_attrs = result.scalar_one()

        # Plaintext secrets MUST NOT exist anywhere
        assert "TopSecretTokenValue123456" not in str(stored_attrs)
        assert "PlaintextSessionCookie987654" not in str(stored_attrs)

        # Redacted placeholders MUST exist
        assert stored_attrs["http.request.header.authorization"] == "[REDACTED]"
        assert stored_attrs["http.request.header.cookie"] == "[REDACTED]"
        assert stored_attrs["http.request.header.accept"] == "application/json"
