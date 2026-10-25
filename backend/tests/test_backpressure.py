import uuid
import pytest
import httpx
from collector.backpressure import BackpressureController, BackpressureExceededError
from collector.http_receiver import app
from storage.db import get_db_session
from storage.models import SpanRecord
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span as ProtoSpan, Status as ProtoStatus
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

def build_test_proto_req(trace_raw: bytes, span_raw: bytes, name: str) -> ExportTraceServiceRequest:
    span = ProtoSpan(
        trace_id=trace_raw,
        span_id=span_raw,
        name=name,
        kind=ProtoSpan.SPAN_KIND_SERVER,
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        status=ProtoStatus(code=ProtoStatus.STATUS_CODE_OK),
    )
    scope_spans = ScopeSpans()
    scope_spans.spans.append(span)
    res_spans = ResourceSpans()
    res_spans.resource.attributes.append(KeyValue(key="service.name", value=AnyValue(string_value="bp-test")))
    res_spans.scope_spans.append(scope_spans)
    req = ExportTraceServiceRequest()
    req.resource_spans.append(res_spans)
    return req


def test_backpressure_controller_limits_and_counters():
    bp = BackpressureController(max_capacity=5)
    assert bp.current_depth == 0
    assert bp.rejected_count == 0

    # Fill up to capacity
    bp.acquire(3)
    assert bp.current_depth == 3
    bp.acquire(2)
    assert bp.current_depth == 5

    # Exceed capacity
    with pytest.raises(BackpressureExceededError) as exc_info:
        bp.acquire(1)

    assert exc_info.value.retry_after_seconds > 0
    assert bp.rejected_count == 1
    assert bp.current_depth == 5  # Bounded memory, does not grow past limit

    # Release items (drain)
    bp.release(2)
    assert bp.current_depth == 3

    # Now admission succeeds
    bp.acquire(1)
    assert bp.current_depth == 4

@pytest.mark.asyncio
async def test_http_endpoint_backpressure_429():
    # Inject backpressure controller with capacity 1
    custom_bp = BackpressureController(max_capacity=1)
    custom_bp.acquire(1)  # Fully saturate

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Patch app's backpressure controller
        old_bp = getattr(app.state, "backpressure", None)
        app.state.backpressure = custom_bp

        try:
            tid = f"tenant-{uuid.uuid4().hex[:8]}"
            resp = await client.post(
                "/v1/traces",
                content=b"dummy",
                headers={
                    "Content-Type": "application/x-protobuf",
                    "X-Tenant-Id": tid,
                }
            )
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
            assert custom_bp.rejected_count >= 1

            # Drain queue and test recovery
            custom_bp.release(1)
            # Valid protobuf trace request after drain should succeed with 200
            t_raw = uuid.uuid4().bytes
            s_raw = uuid.uuid4().bytes[:8]
            req = build_test_proto_req(t_raw, s_raw, "backpressure-recovery-span")
            resp2 = await client.post(
                "/v1/traces",
                content=req.SerializeToString(),
                headers={
                    "Content-Type": "application/x-protobuf",
                    "X-Tenant-Id": tid,
                }
            )
            assert resp2.status_code == 200
        finally:
            app.state.backpressure = old_bp
