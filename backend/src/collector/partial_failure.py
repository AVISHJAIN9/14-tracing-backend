"""
Partial Failure Collector.
Handles heterogeneous span batches, validating spans individually, accumulating
rejected reasons without failing the entire batch, persisting valid spans, and
constructing standardized OpenTelemetry ExportTracePartialSuccess messages.
"""

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTracePartialSuccess
from collector.validator import PayloadValidator, PayloadValidationError
from storage.models import SpanRecord

class PartialFailureCollector:
    def __init__(self, validator: Optional[PayloadValidator] = None):
        self.validator = validator or PayloadValidator()

    async def process_spans_with_partial_failure(
        self,
        session: AsyncSession,
        tenant_id: str,
        raw_spans: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        accepted_records: List[SpanRecord] = []
        errors: List[str] = []

        for item in raw_spans:
            try:
                trace_id = item.get("trace_id", "")
                span_id = item.get("span_id", "")
                if not trace_id or len(trace_id) != 32 or trace_id == "0" * 32:
                    raise PayloadValidationError("Invalid trace_id: must be 32 non-zero hex chars")
                if not span_id or len(span_id) != 16 or span_id == "0" * 16:
                    raise PayloadValidationError("Invalid span_id: must be 16 non-zero hex chars")

                start_nano = item.get("start_time_unix_nano", 0)
                end_nano = item.get("end_time_unix_nano", start_nano)
                duration_nano = self.validator.validate_timestamps(start_nano, end_nano)
                service_name = self.validator.validate_service_name(item.get("service_name"))

                record = SpanRecord(
                    tenant_id=tenant_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=item.get("parent_span_id"),
                    name=item.get("name", "span"),
                    kind=item.get("kind", "INTERNAL"),
                    start_time_unix_nano=start_nano,
                    end_time_unix_nano=end_nano,
                    duration_nanos=duration_nano,
                    status_code=item.get("status_code", "UNSET"),
                    status_message=item.get("status_message"),
                    attributes=item.get("attributes", {}),
                    events=item.get("events", []),
                    links=item.get("links", []),
                    service_name=service_name
                )
                accepted_records.append(record)
            except Exception as e:
                errors.append(f"Span {item.get('span_id', 'unknown')}: {str(e)}")

        if accepted_records:
            session.add_all(accepted_records)
            await session.flush()

        accepted_count = len(accepted_records)
        rejected_count = len(errors)
        return accepted_count, rejected_count, errors

    @staticmethod
    def build_otlp_partial_success(
        rejected_spans: int,
        error_details: List[str]
    ) -> Optional[ExportTracePartialSuccess]:
        if rejected_spans <= 0:
            return None
        return ExportTracePartialSuccess(
            rejected_spans=rejected_spans,
            error_message="; ".join(error_details)
        )
