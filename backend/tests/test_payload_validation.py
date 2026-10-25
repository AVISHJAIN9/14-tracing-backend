import uuid
import pytest
from collector.validator import PayloadValidator, PayloadValidationError
from storage.db import get_db_session
from storage.models import SpanRecord
from security.tenant import TenantService

def test_payload_validator_trace_and_span_ids():
    validator = PayloadValidator()

    # Valid IDs
    t_raw = uuid.uuid4().bytes
    s_raw = uuid.uuid4().bytes[:8]
    t_hex = validator.validate_trace_id(t_raw)
    s_hex = validator.validate_span_id(s_raw)
    assert len(t_hex) == 32
    assert len(s_hex) == 16

    # All-zero trace ID rejected
    with pytest.raises(PayloadValidationError, match="All-zero trace_id is invalid"):
        validator.validate_trace_id(b"\x00" * 16)

    # All-zero span ID rejected
    with pytest.raises(PayloadValidationError, match="All-zero span_id is invalid"):
        validator.validate_span_id(b"\x00" * 8)

    # Invalid length
    with pytest.raises(PayloadValidationError, match="trace_id must be exactly 16 bytes"):
        validator.validate_trace_id(b"\x12" * 15)

    with pytest.raises(PayloadValidationError, match="span_id must be exactly 8 bytes"):
        validator.validate_span_id(b"\x12" * 7)

def test_payload_validator_timestamps():
    validator = PayloadValidator()

    # Valid duration
    dur = validator.validate_timestamps(1000, 2500)
    assert dur == 1500

    # Inverted timestamps
    with pytest.raises(PayloadValidationError, match="end_time_unix_nano.*must be >= start_time"):
        validator.validate_timestamps(2000, 1000)

    # Non-positive start time
    with pytest.raises(PayloadValidationError, match="start_time_unix_nano must be positive"):
        validator.validate_timestamps(0, 1000)

def test_payload_validator_service_name():
    validator = PayloadValidator()

    assert validator.validate_service_name("checkout") == "checkout"

    with pytest.raises(PayloadValidationError, match="Service name cannot be empty"):
        validator.validate_service_name("")

    with pytest.raises(PayloadValidationError, match="Service name cannot be empty"):
        validator.validate_service_name(None)

@pytest.mark.asyncio
async def test_validated_payload_database_persistence():
    validator = PayloadValidator()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    t_raw = uuid.uuid4().bytes
    s_raw = uuid.uuid4().bytes[:8]

    t_hex = validator.validate_trace_id(t_raw)
    s_hex = validator.validate_span_id(s_raw)
    dur = validator.validate_timestamps(1700000000000000000, 1700000001000000000)
    svc = validator.validate_service_name("valid-service")

    record = SpanRecord(
        tenant_id=tid,
        trace_id=t_hex,
        span_id=s_hex,
        parent_span_id=None,
        name="validated-call",
        kind="SERVER",
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        duration_nanos=dur,
        status_code="OK",
        status_message=None,
        attributes={"verified": True},
        events=[],
        links=[],
        service_name=svc
    )
    validator.validate_span_record(record)

    async with get_db_session(tenant_id=tid) as session:
        session.add(record)
        await session.flush()

    async with get_db_session(tenant_id=tid) as session:
        stored = await TenantService.get_spans_for_tenant(session, tid, t_hex)
        assert len(stored) == 1
        assert stored[0].span_id == s_hex
        assert stored[0].service_name == "valid-service"
