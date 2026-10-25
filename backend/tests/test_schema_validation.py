import uuid
import pytest
from collector.schema_validator import OtlpSchemaValidator, SchemaValidationError
from storage.db import get_db_session
from storage.models import SpanRecord
from security.tenant import TenantService

def test_schema_validator_urls():
    validator = OtlpSchemaValidator()

    # Valid schema URLs
    assert validator.validate_schema_url("https://opentelemetry.io/schemas/1.24.0") is True
    assert validator.validate_schema_url("https://opentelemetry.io/schemas/1.7.0") is True
    assert validator.validate_schema_url(None) is True  # Optional

    # Invalid schema URL
    with pytest.raises(SchemaValidationError, match="Unsupported or malformed schema_url"):
        validator.validate_schema_url("ftp://invalid.com/schema")

    with pytest.raises(SchemaValidationError, match="Unsupported or malformed schema_url"):
        validator.validate_schema_url("not-a-url")

def test_schema_validator_attribute_types():
    validator = OtlpSchemaValidator()

    # Valid primitive attributes
    assert validator.validate_attribute("http.status_code", 200) is True
    assert validator.validate_attribute("http.method", "GET") is True
    assert validator.validate_attribute("retry.enabled", True) is True
    assert validator.validate_attribute("latency.ms", 12.5) is True
    assert validator.validate_attribute("tags", ["prod", "us-east-1"]) is True

    # Invalid key: empty
    with pytest.raises(SchemaValidationError, match="Attribute key cannot be empty"):
        validator.validate_attribute("", "value")

    # Invalid key: too long (> 128 chars)
    with pytest.raises(SchemaValidationError, match="Attribute key exceeds maximum length"):
        validator.validate_attribute("x" * 129, "value")

    # Invalid value: arbitrary un-serializable object
    with pytest.raises(SchemaValidationError, match="Unsupported attribute value type"):
        validator.validate_attribute("bad.obj", object())

@pytest.mark.asyncio
async def test_schema_validated_span_persistence():
    validator = OtlpSchemaValidator()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_hex = uuid.uuid4().hex
    span_hex = uuid.uuid4().hex[:16]

    schema_url = "https://opentelemetry.io/schemas/1.24.0"
    validator.validate_schema_url(schema_url)

    attrs = {"http.route": "/api/v1/checkout", "http.status_code": 200}
    for k, v in attrs.items():
        validator.validate_attribute(k, v)

    span = SpanRecord(
        tenant_id=tid,
        trace_id=trace_hex,
        span_id=span_hex,
        parent_span_id=None,
        name="checkout-route",
        kind="SERVER",
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        duration_nanos=1000000000,
        status_code="OK",
        status_message=None,
        attributes=attrs,
        events=[],
        links=[],
        service_name="frontend-proxy"
    )

    async with get_db_session(tenant_id=tid) as session:
        session.add(span)
        await session.flush()

    async with get_db_session(tenant_id=tid) as session:
        stored = await TenantService.get_spans_for_tenant(session, tid, trace_hex)
        assert len(stored) == 1
        assert stored[0].attributes["http.status_code"] == 200
