"""
OTLP/HTTP Receiver.
FastAPI router and application providing the official OpenTelemetry HTTP endpoint at /v1/traces,
supporting both binary protobuf (application/x-protobuf) and JSON (application/json) payloads.
Extracts tenant context and persists normalized traces to PostgreSQL.
"""

from typing import Optional
from fastapi import FastAPI, Request, Response, Header, HTTPException, status
from google.protobuf.json_format import ParseDict, MessageToDict, ParseError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
    ExportTracePartialSuccess,
)

from storage.db import get_db_session
from collector.otlp import OtlpIngestService
from collector.backpressure import BackpressureController, BackpressureExceededError

app = FastAPI(title="OTLP HTTP Collector Receiver", version="1.0.0")
app.state.backpressure = BackpressureController()
_ingest_service = OtlpIngestService()

@app.post("/v1/traces")
async def export_traces(
    request: Request,
    content_type: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header("default-tenant"),
) -> Response:
    bp = getattr(request.app.state, "backpressure", None)
    if bp:
        try:
            bp.acquire(1)
        except BackpressureExceededError as e:
            return Response(
                content=f'{{"error": "Too Many Requests", "detail": "{str(e)}"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(e.retry_after_seconds)}
            )

    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request body")

        tenant_id = x_tenant_id or "default-tenant"
        proto_req = ExportTraceServiceRequest()

        ct = (content_type or "").lower()
        is_json = "application/json" in ct

        if is_json:
            try:
                json_data = await request.json()
                ParseDict(json_data, proto_req, ignore_unknown_fields=True)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Malformed JSON payload: {str(e)}"
                )
        else:
            # Binary protobuf
            try:
                proto_req.ParseFromString(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Malformed Protobuf payload: {str(e)}"
                )

        async with get_db_session(tenant_id=tenant_id) as session:
            result = await _ingest_service.ingest_export_request(session, tenant_id, proto_req)

        proto_resp = ExportTraceServiceResponse()
        if result.rejected_spans > 0:
            proto_resp.partial_success.CopyFrom(
                ExportTracePartialSuccess(
                    rejected_spans=result.rejected_spans,
                    error_message="; ".join(result.error_details),
                )
            )

        accept = request.headers.get("accept", "").lower()
        if "application/json" in accept or is_json:
            resp_dict = MessageToDict(proto_resp)
            return Response(
                content=request.app.state.json_serializer(resp_dict) if hasattr(request.app.state, "json_serializer") else __import__("json").dumps(resp_dict),
                media_type="application/json",
                status_code=200,
            )
        else:
            return Response(
                content=proto_resp.SerializeToString(),
                media_type="application/x-protobuf",
                status_code=200,
            )
    finally:
        if bp:
            bp.release(1)

