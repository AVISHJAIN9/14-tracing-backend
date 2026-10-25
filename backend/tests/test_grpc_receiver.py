import uuid
import pytest
import grpc.aio
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
import opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc as trace_service_pb2_grpc
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span as ProtoSpan,
    Status as ProtoStatus,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

from collector.grpc_receiver import create_grpc_collector_server, OtlpGrpcTraceService
from storage.db import get_db_session
from security.tenant import TenantService

def build_test_proto_request(trace_raw: bytes, span_raw: bytes) -> ExportTraceServiceRequest:
    span = ProtoSpan(
        trace_id=trace_raw,
        span_id=span_raw,
        name="grpc-client-call",
        kind=ProtoSpan.SPAN_KIND_SERVER,
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        status=ProtoStatus(code=ProtoStatus.STATUS_CODE_OK),
    )
    span.attributes.append(KeyValue(key="rpc.method", value=AnyValue(string_value="Export")))

    scope_spans = ScopeSpans()
    scope_spans.spans.append(span)

    res_spans = ResourceSpans()
    res_spans.resource.attributes.append(
        KeyValue(key="service.name", value=AnyValue(string_value="payment-service"))
    )
    res_spans.scope_spans.append(scope_spans)

    req = ExportTraceServiceRequest()
    req.resource_spans.append(res_spans)
    return req

@pytest.mark.asyncio
async def test_otlp_grpc_receiver_live_network_ingestion():
    port = 44317
    server = create_grpc_collector_server(port=port)
    await server.start()

    try:
        channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
        stub = trace_service_pb2_grpc.TraceServiceStub(channel)

        tid = f"tenant-{uuid.uuid4().hex[:8]}"
        trace_raw = uuid.uuid4().bytes
        span_raw = uuid.uuid4().bytes[:8]
        trace_hex = trace_raw.hex()
        span_hex = span_raw.hex()

        request = build_test_proto_request(trace_raw, span_raw)

        # Call gRPC Export over real TCP socket with tenant metadata
        response: ExportTraceServiceResponse = await stub.Export(
            request,
            metadata=(("x-tenant-id", tid),)
        )

        assert isinstance(response, ExportTraceServiceResponse)
        if response.partial_success:
            assert response.partial_success.rejected_spans == 0

        # Verify persisted span in PostgreSQL 16
        async with get_db_session(tenant_id=tid) as session:
            spans = await TenantService.get_spans_for_tenant(session, tid, trace_hex)
            assert len(spans) == 1
            stored = spans[0]
            assert stored.span_id == span_hex
            assert stored.service_name == "payment-service"
            assert stored.name == "grpc-client-call"
            assert stored.status_code == "OK"

        await channel.close()
    finally:
        await server.stop(grace=None)
