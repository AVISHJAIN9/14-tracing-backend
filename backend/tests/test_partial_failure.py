import uuid
import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTracePartialSuccess
from collector.partial_failure import PartialFailureCollector
from storage.db import get_db_session
from security.tenant import TenantService

@pytest.mark.asyncio
async def test_partial_failure_handling_and_otlp_response():
    collector = PartialFailureCollector()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"

    valid_trace = uuid.uuid4().hex
    valid_span1 = uuid.uuid4().hex[:16]
    valid_span2 = uuid.uuid4().hex[:16]

    items = [
        # 1. Valid span 1
        {
            "trace_id": valid_trace,
            "span_id": valid_span1,
            "name": "partial-valid-1",
            "service_name": "billing-service",
            "start_time_unix_nano": 1700000000000000000,
            "end_time_unix_nano": 1700000001000000000,
        },
        # 2. Inverted timestamps (end < start) -> Should fail
        {
            "trace_id": valid_trace,
            "span_id": uuid.uuid4().hex[:16],
            "name": "partial-invalid-timing",
            "service_name": "billing-service",
            "start_time_unix_nano": 1700000002000000000,
            "end_time_unix_nano": 1700000001000000000,
        },
        # 3. Valid span 2
        {
            "trace_id": valid_trace,
            "span_id": valid_span2,
            "name": "partial-valid-2",
            "service_name": "billing-service",
            "start_time_unix_nano": 1700000000000000000,
            "end_time_unix_nano": 1700000001000000000,
        },
        # 4. All-zero trace_id -> Should fail
        {
            "trace_id": "0" * 32,
            "span_id": uuid.uuid4().hex[:16],
            "name": "partial-invalid-trace-id",
            "service_name": "billing-service",
            "start_time_unix_nano": 1700000000000000000,
            "end_time_unix_nano": 1700000001000000000,
        }
    ]

    async with get_db_session(tenant_id=tid) as session:
        accepted, rejected, errors = await collector.process_spans_with_partial_failure(
            session=session,
            tenant_id=tid,
            raw_spans=items
        )

    assert accepted == 2
    assert rejected == 2
    assert len(errors) == 2
    assert any("end_time_unix_nano" in e for e in errors)
    assert any("trace_id" in e for e in errors)

    # Verify standard OTLP partial success response object construction
    partial_success_obj = collector.build_otlp_partial_success(rejected, errors)
    assert isinstance(partial_success_obj, ExportTracePartialSuccess)
    assert partial_success_obj.rejected_spans == 2
    assert len(partial_success_obj.error_message) > 0

    # Verify PostgreSQL 16 persistence
    async with get_db_session(tenant_id=tid) as session:
        spans = await TenantService.get_spans_for_tenant(session, tid, valid_trace)
        assert len(spans) == 2
        names = {s.name for s in spans}
        assert names == {"partial-valid-1", "partial-valid-2"}
