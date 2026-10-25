import uuid
import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span as ProtoSpan,
    Status as ProtoStatus,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

from collector.otlp import OtlpIngestService
from storage.db import get_db_session
from security.tenant import TenantService

@pytest.mark.asyncio
async def test_mixed_batch_malformed_span_handling():
    ingester = OtlpIngestService()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"

    valid_trace_raw = uuid.uuid4().bytes
    valid_span1_raw = uuid.uuid4().bytes[:8]
    valid_span3_raw = uuid.uuid4().bytes[:8]
    malformed_span_raw = b"\x00" * 8  # All-zero span_id (invalid per spec)

    # 1. Valid span 1
    s1 = ProtoSpan(
        trace_id=valid_trace_raw,
        span_id=valid_span1_raw,
        name="valid-span-1",
        kind=ProtoSpan.SPAN_KIND_SERVER,
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        status=ProtoStatus(code=ProtoStatus.STATUS_CODE_OK),
    )

    # 2. Malformed span 2 (all-zero span_id)
    s2 = ProtoSpan(
        trace_id=valid_trace_raw,
        span_id=malformed_span_raw,
        name="malformed-span-2",
        kind=ProtoSpan.SPAN_KIND_SERVER,
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        status=ProtoStatus(code=ProtoStatus.STATUS_CODE_OK),
    )

    # 3. Valid span 3
    s3 = ProtoSpan(
        trace_id=valid_trace_raw,
        span_id=valid_span3_raw,
        name="valid-span-3",
        kind=ProtoSpan.SPAN_KIND_SERVER,
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        status=ProtoStatus(code=ProtoStatus.STATUS_CODE_OK),
    )

    scope_spans = ScopeSpans()
    scope_spans.spans.extend([s1, s2, s3])

    res_spans = ResourceSpans()
    res_spans.resource.attributes.append(
        KeyValue(key="service.name", value=AnyValue(string_value="order-service"))
    )
    res_spans.scope_spans.append(scope_spans)

    req = ExportTraceServiceRequest()
    req.resource_spans.append(res_spans)

    # Ingest mixed batch
    async with get_db_session(tenant_id=tid) as session:
        result = await ingester.ingest_export_request(session, tid, req)
        assert result.accepted_spans == 2
        assert result.rejected_spans == 1
        assert len(result.error_details) == 1
        assert "All-zero span_id is invalid" in result.error_details[0]

    # Verify only valid spans are stored in PostgreSQL 16
    async with get_db_session(tenant_id=tid) as session:
        stored_spans = await TenantService.get_spans_for_tenant(session, tid, valid_trace_raw.hex())
        assert len(stored_spans) == 2
        names = {s.name for s in stored_spans}
        assert names == {"valid-span-1", "valid-span-3"}
        assert "malformed-span-2" not in names
