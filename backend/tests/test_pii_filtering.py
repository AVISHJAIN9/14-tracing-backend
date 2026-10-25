import pytest
import uuid
from sqlalchemy import text
from storage.db import get_db_session
from storage.models import SpanRecord
from security.pii_filter import PiiFilter

def test_pii_pattern_sanitization():
    pii_filter = PiiFilter()
    sample = (
        "User john.doe@example.com (SSN: 123-45-6789, phone: +1-555-867-5309) "
        "connected from 192.168.1.105 with payment card 4111222233334444."
    )
    sanitized = pii_filter.sanitize_string(sample)

    assert "john.doe@example.com" not in sanitized
    assert "123-45-6789" not in sanitized
    assert "555-867-5309" not in sanitized
    assert "192.168.1.105" not in sanitized
    assert "4111222233334444" not in sanitized

    assert "[EMAIL_REDACTED]" in sanitized
    assert "[SSN_REDACTED]" in sanitized
    assert "[PHONE_REDACTED]" in sanitized
    assert "[IP_REDACTED]" in sanitized
    assert "[CARD_REDACTED]" in sanitized

def test_pii_nested_data_sanitization():
    pii_filter = PiiFilter()
    data = {
        "user_info": {
            "contact": "alice.smith@corp.org",
            "notes": "Emergency phone: 212-555-0199"
        },
        "history": [
            {"event": "Login from 10.0.0.50"},
            {"event": "Verified tax ID 987-65-4321"}
        ]
    }
    cleaned = pii_filter.sanitize_data(data)

    assert cleaned["user_info"]["contact"] == "[EMAIL_REDACTED]"
    assert "[PHONE_REDACTED]" in cleaned["user_info"]["notes"]
    assert "[IP_REDACTED]" in cleaned["history"][0]["event"]
    assert "[SSN_REDACTED]" in cleaned["history"][1]["event"]

@pytest.mark.asyncio
async def test_pii_filtering_persisted_to_postgres():
    """
    Assert invariant: PII is filtered prior to storage in PostgreSQL,
    and raw database inspection proves plaintext email/SSN/IP are absent from disk.
    """
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]

    pii_filter = PiiFilter()

    raw_attributes = {
        "statement": "Customer bob.marley@reggae.jam queried account with SSN 456-78-1234",
        "client_ip": "172.16.254.1"
    }
    raw_status = "Error processing request for user.contact: marley@music.com"

    cleaned_attrs = pii_filter.sanitize_data(raw_attributes)
    cleaned_status = pii_filter.sanitize_string(raw_status)

    async with get_db_session(tenant_id=tid) as session:
        span = SpanRecord(
            tenant_id=tid,
            trace_id=trace_id,
            span_id=span_id,
            name="ProcessUserData",
            kind="INTERNAL",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000100000000,
            duration_nanos=100000000,
            status_code="ERROR",
            status_message=cleaned_status,
            attributes=cleaned_attrs,
            events=[],
            links=[],
            service_name="profile-service"
        )
        session.add(span)

    # Inspect raw table in PostgreSQL
    async with get_db_session(tenant_id=tid) as session:
        result = await session.execute(
            text(f"SELECT attributes, status_message FROM spans WHERE tenant_id = '{tid}' AND span_id = '{span_id}'")
        )
        row = result.fetchone()
        assert row is not None
        stored_attrs, stored_status = row

        # Plaintext PII MUST NOT exist anywhere
        assert "bob.marley@reggae.jam" not in str(stored_attrs)
        assert "456-78-1234" not in str(stored_attrs)
        assert "172.16.254.1" not in str(stored_attrs)
        assert "marley@music.com" not in stored_status

        # Redacted tokens MUST exist
        assert "[EMAIL_REDACTED]" in str(stored_attrs)
        assert "[SSN_REDACTED]" in str(stored_attrs)
        assert "[IP_REDACTED]" in str(stored_attrs)
        assert "[EMAIL_REDACTED]" in stored_status
