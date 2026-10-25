import uuid
import pytest
import httpx
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span as ProtoSpan,
    Status as ProtoStatus,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

from collector.http_receiver import app
from storage.db import get_db_session
from security.tenant import TenantService

def build_test_proto(trace_raw: bytes, span_raw: bytes, name: str) -> ExportTraceServiceRequest:
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
    res_spans.resource.attributes.append(
        KeyValue(key="service.name", value=AnyValue(string_value="order-api"))
    )
    res_spans.scope_spans.append(scope_spans)

    req = ExportTraceServiceRequest()
    req.resource_spans.append(res_spans)
    return req

@pytest.mark.asyncio
async def test_otlp_http_receiver_protobuf_and_json():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Protobuf ingestion
        tid = f"tenant-{uuid.uuid4().hex[:8]}"
        trace_raw1 = uuid.uuid4().bytes
        span_raw1 = uuid.uuid4().bytes[:8]
        req1 = build_test_proto(trace_raw1, span_raw1, "http-protobuf-span")

        resp1 = await client.post(
            "/v1/traces",
            content=req1.SerializeToString(),
            headers={
                "Content-Type": "application/x-protobuf",
                "X-Tenant-Id": tid,
            }
        )
        assert resp1.status_code == 200
        pb_resp = ExportTraceServiceResponse()
        pb_resp.ParseFromString(resp1.content)

        # 2. Test JSON ingestion
        trace_raw2 = uuid.uuid4().bytes
        span_raw2 = uuid.uuid4().bytes[:8]
        req2 = build_test_proto(trace_raw2, span_raw2, "http-json-span")
        json_dict = MessageToDict(req2)

        resp2 = await client.post(
            "/v1/traces",
            json=json_dict,
            headers={
                "Content-Type": "application/json",
                "X-Tenant-Id": tid,
            }
        )
        assert resp2.status_code == 200
        assert "partialSuccess" in resp2.json() or resp2.json() == {}

        # 3. Verify both spans stored in PostgreSQL 16
        async with get_db_session(tenant_id=tid) as session:
            spans1 = await TenantService.get_spans_for_tenant(session, tid, trace_raw1.hex())
            assert len(spans1) == 1
            assert spans1[0].name == "http-protobuf-span"
            assert spans1[0].service_name == "order-api"

            spans2 = await TenantService.get_spans_for_tenant(session, tid, trace_raw2.hex())
            assert len(spans2) == 1
            assert spans2[0].name == "http-json-span"
            assert spans2[0].service_name == "order-api"

        # 4. Test malformed payload handling
        resp_err = await client.post(
            "/v1/traces",
            content=b"not-a-valid-proto",
            headers={
                "Content-Type": "application/x-protobuf",
                "X-Tenant-Id": tid,
            }
        )
        assert resp_err.status_code == 400
