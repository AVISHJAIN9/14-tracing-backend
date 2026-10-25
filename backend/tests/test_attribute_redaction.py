import pytest
import uuid
from sqlalchemy import text
from storage.db import get_db_session
from storage.models import SpanRecord
from security.redaction import AttributeRedactor

def test_sensitive_attribute_redaction_top_and_nested():
    redactor = AttributeRedactor()
    attrs = {
        "http.method": "POST",
        "http.url": "https://api.example.com/login",
        "password": "superSecretPassword123!",
        "api_key": "trc_live_secretkey",
        "db": {
            "user": "postgres",
            "password": "db_master_password",
            "query": "SELECT * FROM users"
        },
        "tokens": [
            {"type": "jwt", "token": "eyJhbGciOi..."},
            {"type": "refresh", "secret": "refresh_abc"}
        ]
    }

    cleaned = redactor.redact_span_attributes(attrs)

    # Sensitive values masked
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["db"]["password"] == "[REDACTED]"
    assert cleaned["tokens"][0]["token"] == "[REDACTED]"
    assert cleaned["tokens"][1]["secret"] == "[REDACTED]"

    # Non-sensitive preserved
    assert cleaned["http.method"] == "POST"
    assert cleaned["db"]["user"] == "postgres"
    assert cleaned["tokens"][0]["type"] == "jwt"

@pytest.mark.asyncio
async def test_sensitive_attribute_redaction_persisted_to_postgres():
    """
    Assert invariant: sensitive attributes are redacted BEFORE hitting PostgreSQL,
    and raw database JSONB inspection proves the sensitive secret never reaches disk.
    """
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]

    redactor = AttributeRedactor()
    raw_incoming_attributes = {
        "service.name": "checkout-svc",
        "user.email": "customer@shop.com",
        "credit_card": "4111-2222-3333-4444",
        "card_number": "5500-0000-0000-0004",
        "cvv": "999",
        "session_token": "secret_session_token_xyz"
    }

    redacted_attrs = redactor.redact_span_attributes(raw_incoming_attributes)

    async with get_db_session(tenant_id=tid) as session:
        span = SpanRecord(
            tenant_id=tid,
            trace_id=trace_id,
            span_id=span_id,
            name="CheckoutCharge",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000100000000,
            duration_nanos=100000000,
            status_code="OK",
            attributes=redacted_attrs,
            events=[],
            links=[],
            service_name="checkout-svc"
        )
        session.add(span)

    # Inspect raw table rows in PostgreSQL
    async with get_db_session(tenant_id=tid) as session:
        result = await session.execute(
            text(f"SELECT attributes FROM spans WHERE tenant_id = '{tid}' AND span_id = '{span_id}'")
        )
        stored_attrs = result.scalar_one()

        # 1. Plaintext secrets MUST NOT exist anywhere in stored JSONB
        assert "4111-2222-3333-4444" not in str(stored_attrs)
        assert "5500-0000-0000-0004" not in str(stored_attrs)
        assert "999" not in str(stored_attrs)
        assert "secret_session_token_xyz" not in str(stored_attrs)

        # 2. Redacted placeholders MUST exist
        assert stored_attrs["credit_card"] == "[REDACTED]"
        assert stored_attrs["card_number"] == "[REDACTED]"
        assert stored_attrs["cvv"] == "[REDACTED]"
        assert stored_attrs["session_token"] == "[REDACTED]"
        assert stored_attrs["service.name"] == "checkout-svc"
