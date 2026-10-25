"""
OTLP (OpenTelemetry Protocol) Ingestion Engine.
Parses official protobuf ExportTraceServiceRequest payloads, normalizes spans,
applies tenant isolation, redaction, and PII filtering, and stores records in PostgreSQL.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse
)
from opentelemetry.proto.trace.v1.trace_pb2 import Span as ProtoSpan
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord, TraceRecord
from security.redaction import AttributeRedactor
from security.pii_filter import PiiFilter
from collector.validator import PayloadValidator, PayloadValidationError

@dataclass
class OtlpIngestResult:
    accepted_spans: int = 0
    rejected_spans: int = 0
    error_details: List[str] = field(default_factory=list)

class OtlpIngestService:
    def __init__(
        self,
        redactor: Optional[AttributeRedactor] = None,
        pii_filter: Optional[PiiFilter] = None,
        validator: Optional[PayloadValidator] = None,
    ):
        self.redactor = redactor or AttributeRedactor()
        self.pii_filter = pii_filter or PiiFilter()
        self.validator = validator or PayloadValidator()

    @staticmethod
    def parse_protobuf_bytes(data: bytes) -> ExportTraceServiceRequest:
        request = ExportTraceServiceRequest()
        request.ParseFromString(data)
        return request

    def _convert_proto_any_value(self, any_val: Any) -> Any:
        field_name = any_val.WhichOneof("value")
        if field_name == "string_value":
            return any_val.string_value
        elif field_name == "bool_value":
            return any_val.bool_value
        elif field_name == "int_value":
            return any_val.int_value
        elif field_name == "double_value":
            return any_val.double_value
        elif field_name == "array_value":
            return [self._convert_proto_any_value(v) for v in any_val.array_value.values]
        elif field_name == "kvlist_value":
            return {kv.key: self._convert_proto_any_value(kv.value) for kv in any_val.kvlist_value.values}
        return None

    def _extract_attributes(self, key_values: Any) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {}
        for kv in key_values:
            attrs[kv.key] = self._convert_proto_any_value(kv.value)
        return attrs

    def normalize_proto_span(
        self,
        tenant_id: str,
        proto_span: ProtoSpan,
        resource_attributes: Dict[str, Any]
    ) -> SpanRecord:
        trace_id_hex = self.validator.validate_trace_id(proto_span.trace_id)
        span_id_hex = self.validator.validate_span_id(proto_span.span_id)
        parent_id_hex = self.validator.validate_span_id(proto_span.parent_span_id) if proto_span.parent_span_id else None

        raw_attrs = self._extract_attributes(proto_span.attributes)
        raw_attrs.update(resource_attributes)

        # Apply security redaction and PII filtering
        cleaned_attrs = self.redactor.redact_span_attributes(raw_attrs)
        sanitized_attrs = self.pii_filter.sanitize_data(cleaned_attrs)

        # Status code and message
        status_code = "UNSET"
        if proto_span.status.code == 1:
            status_code = "OK"
        elif proto_span.status.code == 2:
            status_code = "ERROR"

        status_msg = proto_span.status.message or None
        if status_msg:
            status_msg = self.pii_filter.sanitize_string(status_msg)

        # Span kind enum string
        kind_map = {0: "INTERNAL", 1: "INTERNAL", 2: "SERVER", 3: "CLIENT", 4: "PRODUCER", 5: "CONSUMER"}
        span_kind = kind_map.get(proto_span.kind, "INTERNAL")

        service_name = self.validator.validate_service_name(str(resource_attributes.get("service.name") or "unknown_service"))

        start_nano = proto_span.start_time_unix_nano
        end_nano = proto_span.end_time_unix_nano or start_nano
        duration_nano = self.validator.validate_timestamps(start_nano, end_nano)

        # Events
        events_list: List[Dict[str, Any]] = []
        for ev in proto_span.events:
            ev_attrs = self.pii_filter.sanitize_data(self._extract_attributes(ev.attributes))
            ev_name = self.pii_filter.sanitize_string(ev.name)
            events_list.append({
                "time_unix_nano": ev.time_unix_nano,
                "name": ev_name,
                "attributes": ev_attrs
            })

        # Links
        links_list: List[Dict[str, Any]] = []
        for lk in proto_span.links:
            lk_attrs = self._extract_attributes(lk.attributes)
            links_list.append({
                "trace_id": lk.trace_id.hex(),
                "span_id": lk.span_id.hex(),
                "attributes": lk_attrs
            })

        return SpanRecord(
            tenant_id=tenant_id,
            trace_id=trace_id_hex,
            span_id=span_id_hex,
            parent_span_id=parent_id_hex,
            name=proto_span.name,
            kind=span_kind,
            start_time_unix_nano=start_nano,
            end_time_unix_nano=end_nano,
            duration_nanos=duration_nano,
            status_code=status_code,
            status_message=status_msg,
            attributes=sanitized_attrs,
            events=events_list,
            links=links_list,
            service_name=service_name
        )

    async def ingest_export_request(
        self,
        session: AsyncSession,
        tenant_id: str,
        request: ExportTraceServiceRequest
    ) -> OtlpIngestResult:
        result = OtlpIngestResult()

        for resource_spans in request.resource_spans:
            res_attrs = self._extract_attributes(resource_spans.resource.attributes)
            for scope_spans in resource_spans.scope_spans:
                for proto_span in scope_spans.spans:
                    try:
                        record = self.normalize_proto_span(tenant_id, proto_span, res_attrs)
                        session.add(record)
                        result.accepted_spans += 1
                    except Exception as e:
                        result.rejected_spans += 1
                        result.error_details.append(f"Span {proto_span.span_id.hex()}: {str(e)}")

        await session.flush()
        return result

    async def batch_ingest_records(
        self,
        session: AsyncSession,
        tenant_id: str,
        records: List[SpanRecord],
        batch_size: int = 500
    ) -> int:
        if not records:
            return 0
        total_ingested = 0
        for i in range(0, len(records), batch_size):
            chunk = records[i:i + batch_size]
            for rec in chunk:
                rec.tenant_id = tenant_id
            session.add_all(chunk)
            await session.flush()
            total_ingested += len(chunk)
        return total_ingested

