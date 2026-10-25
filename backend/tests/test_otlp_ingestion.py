import pytest
import uuid
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span as ProtoSpan,
    Status as ProtoStatus
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue
from storage.db import get_db_session
from security.tenant import TenantService
from collector.otlp import OtlpIngestService

def make_string_kv(key: str, value: str) -> KeyValue:
    kv = KeyValue()
    kv.key = key
    kv.value.string_value = value
    return kv

def make_int_kv(key: str, value: int) -> KeyValue:
    kv = KeyValue()
    kv.key = key
    kv.value.int_value = value
    return kv

def build_otlp_request(trace_bytes: bytes, span1_bytes: bytes, span2_bytes: bytes) -> ExportTraceServiceRequest:
    req = ExportTraceServiceRequest()
    rs = req.resource_spans.add()
    rs.resource.attributes.extend([
        make_string_kv("service.name", "order-processor"),
        make_string_kv("deployment.environment", "production")
    ])

    scope = rs.scope_spans.add()
    scope.scope.name = "my.tracer"

    # Span 1 (root)
    s1 = scope.spans.add()
    s1.trace_id = trace_bytes
    s1.span_id = span1_bytes
    s1.name = "POST /orders"
    s1.kind = 2 # SERVER
    s1.start_time_unix_nano = 1700000000000000000
    s1.end_time_unix_nano = 1700000000200000000
    s1.status.code = 1 # OK
    s1.attributes.extend([
        make_string_kv("http.method", "POST"),
        make_int_kv("http.status_code", 200)
    ])

    # Span 2 (child)
    s2 = scope.spans.add()
    s2.trace_id = trace_bytes
    s2.span_id = span2_bytes
    s2.parent_span_id = span1_bytes
    s2.name = "db.query SELECT"
    s2.kind = 3 # CLIENT
    s2.start_time_unix_nano = 1700000000050000000
    s2.end_time_unix_nano = 1700000000150000000
    s2.status.code = 1
    s2.attributes.extend([
        make_string_kv("db.system", "postgresql")
    ])

    return req

@pytest.mark.asyncio
async def test_otlp_protobuf_ingest_and_postgres_storage():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_raw = uuid.uuid4().bytes
    span1_raw = uuid.uuid4().bytes[:8]
    span2_raw = uuid.uuid4().bytes[:8]

    trace_hex = trace_raw.hex()
    span1_hex = span1_raw.hex()
    span2_hex = span2_raw.hex()

    req = build_otlp_request(trace_raw, span1_raw, span2_raw)
    raw_proto_bytes = req.SerializeToString()

    # 1. Parse raw bytes back
    parsed_req = OtlpIngestService.parse_protobuf_bytes(raw_proto_bytes)
    assert len(parsed_req.resource_spans) == 1
    assert len(parsed_req.resource_spans[0].scope_spans[0].spans) == 2

    # 2. Ingest into PostgreSQL
    ingester = OtlpIngestService()
    async with get_db_session(tenant_id=tid) as session:
        result = await ingester.ingest_export_request(session, tid, parsed_req)
        assert result.accepted_spans == 2
        assert result.rejected_spans == 0

    # 3. Verify records stored in PostgreSQL
    async with get_db_session(tenant_id=tid) as session:
        spans = await TenantService.get_spans_for_tenant(session, tid, trace_hex)
        assert len(spans) == 2

        span_map = {s.span_id: s for s in spans}
        assert span1_hex in span_map
        assert span2_hex in span_map

        root = span_map[span1_hex]
        assert root.name == "POST /orders"
        assert root.kind == "SERVER"
        assert root.service_name == "order-processor"
        assert root.attributes["http.method"] == "POST"
        assert root.duration_nanos == 200000000

        child = span_map[span2_hex]
        assert child.parent_span_id == span1_hex
        assert child.name == "db.query SELECT"
        assert child.attributes["db.system"] == "postgresql"
