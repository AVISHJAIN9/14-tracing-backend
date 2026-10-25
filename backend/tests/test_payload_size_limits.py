import pytest
import uuid
from storage.db import get_db_session
from storage.models import SpanRecord
from security.payload_limiter import (
    PayloadLimiter,
    PayloadLimitsConfig,
    PayloadTooLargeError
)

def test_request_body_byte_size_limits():
    config = PayloadLimitsConfig(max_payload_bytes=1024) # 1 KB limit for testing
    limiter = PayloadLimiter(config)

    # 1. Below limit succeeds
    small_payload = b"x" * 500
    limiter.validate_request_bytes(small_payload)

    # 2. Above limit raises PayloadTooLargeError
    large_payload = b"x" * 1500
    with pytest.raises(PayloadTooLargeError, match="exceeds maximum allowed limit"):
        limiter.validate_request_bytes(large_payload)

def test_attribute_and_string_truncation():
    config = PayloadLimitsConfig(
        max_attributes_count=5,
        max_attribute_string_length=50,
        max_events_count=3,
        max_links_count=2
    )
    limiter = PayloadLimiter(config)

    # 10 attributes, one huge string
    raw_attrs = {f"key_{i}": f"value_{i}" for i in range(10)}
    raw_attrs["huge_string"] = "A" * 200

    sanitized_attrs = limiter.sanitize_attributes(raw_attrs)

    # Capped to 5 attributes
    assert len(sanitized_attrs) == 5

    # Test string truncation
    truncated_val = limiter._truncate_string("B" * 100)
    assert len(truncated_val) <= 50
    assert "...[TRUNCATED]" in truncated_val

    # Events and links capped
    raw_events = [{"name": f"event_{i}"} for i in range(10)]
    raw_links = [{"trace_id": f"t_{i}"} for i in range(10)]

    events = limiter.sanitize_events(raw_events)
    links = limiter.sanitize_links(raw_links)

    assert len(events) == 3
    assert len(links) == 2

@pytest.mark.asyncio
async def test_payload_limits_persisted_to_postgres():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]

    config = PayloadLimitsConfig(max_attributes_count=4, max_attribute_string_length=30)
    limiter = PayloadLimiter(config)

    raw_attrs = {
        "short_key": "ok",
        "long_key": "This is a very long string value that exceeds 30 characters easily",
        "k1": "v1",
        "k2": "v2",
        "k3_overflow": "should_be_dropped",
        "k4_overflow": "should_be_dropped"
    }

    clean_attrs, clean_events, clean_links = limiter.sanitize_span_payload(
        raw_attrs, events=[{"e": 1}], links=[]
    )

    assert len(clean_attrs) == 4
    assert "...[TRUNCATED]" in clean_attrs["long_key"]

    async with get_db_session(tenant_id=tid) as session:
        span = SpanRecord(
            tenant_id=tid,
            trace_id=trace_id,
            span_id=span_id,
            name="SanitizedSpan",
            kind="INTERNAL",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000010000000,
            duration_nanos=10000000,
            status_code="OK",
            attributes=clean_attrs,
            events=clean_events,
            links=clean_links,
            service_name="sanitized-svc"
        )
        session.add(span)

    # Verify retrieval from PostgreSQL
    async with get_db_session(tenant_id=tid) as session:
        from security.tenant import TenantService
        spans = await TenantService.get_spans_for_tenant(session, tid, trace_id)
        assert len(spans) == 1
        stored = spans[0]
        assert len(stored.attributes) == 4
        assert "...[TRUNCATED]" in stored.attributes["long_key"]
        assert "k3_overflow" not in stored.attributes
