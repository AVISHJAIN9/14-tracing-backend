"""
OTLP/gRPC Receiver.
Implements the OpenTelemetry TraceService gRPC interface over a network socket,
extracts tenant context from invocation metadata, passes requests to the ingestion
engine, and returns standardized ExportTraceServiceResponse messages.
"""

from typing import Optional
import grpc.aio
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
    ExportTracePartialSuccess,
)
import opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc as trace_service_pb2_grpc

from storage.db import get_db_session
from collector.otlp import OtlpIngestService

class OtlpGrpcTraceService(trace_service_pb2_grpc.TraceServiceServicer):
    def __init__(self, ingest_service: Optional[OtlpIngestService] = None):
        self.ingest_service = ingest_service or OtlpIngestService()

    async def Export(
        self,
        request: ExportTraceServiceRequest,
        context: grpc.aio.ServicerContext,
    ) -> ExportTraceServiceResponse:
        metadata = dict(context.invocation_metadata())
        tenant_id = metadata.get("x-tenant-id", "default-tenant")

        async with get_db_session(tenant_id=tenant_id) as session:
            result = await self.ingest_service.ingest_export_request(
                session, tenant_id, request
            )

        partial_success: Optional[ExportTracePartialSuccess] = None
        if result.rejected_spans > 0:
            partial_success = ExportTracePartialSuccess(
                rejected_spans=result.rejected_spans,
                error_message="; ".join(result.error_details),
            )

        return ExportTraceServiceResponse(partial_success=partial_success)

def create_grpc_collector_server(
    port: int = 4317,
    servicer: Optional[OtlpGrpcTraceService] = None,
) -> grpc.aio.Server:
    server = grpc.aio.server()
    srv = servicer or OtlpGrpcTraceService()
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(srv, server)
    server.add_insecure_port(f"0.0.0.0:{port}")
    return server
