"""
Payload Validator.
Strict validation of OpenTelemetry span IDs, trace IDs, timestamps,
service names, and record invariants before storage.
"""

from typing import Optional
from storage.models import SpanRecord

class PayloadValidationError(Exception):
    """Raised when an ingested span payload violates specification constraints."""
    pass

class PayloadValidator:
    @staticmethod
    def validate_trace_id(trace_id_bytes: bytes) -> str:
        if len(trace_id_bytes) != 16:
            raise PayloadValidationError(f"trace_id must be exactly 16 bytes, got {len(trace_id_bytes)}")
        if trace_id_bytes == b"\x00" * 16:
            raise PayloadValidationError("All-zero trace_id is invalid")
        return trace_id_bytes.hex()

    @staticmethod
    def validate_span_id(span_id_bytes: bytes) -> str:
        if len(span_id_bytes) != 8:
            raise PayloadValidationError(f"span_id must be exactly 8 bytes, got {len(span_id_bytes)}")
        if span_id_bytes == b"\x00" * 8:
            raise PayloadValidationError("All-zero span_id is invalid")
        return span_id_bytes.hex()

    @staticmethod
    def validate_timestamps(start_nano: int, end_nano: int) -> int:
        if start_nano <= 0:
            raise PayloadValidationError("start_time_unix_nano must be positive")
        if end_nano < start_nano:
            raise PayloadValidationError(f"end_time_unix_nano ({end_nano}) must be >= start_time ({start_nano})")
        return end_nano - start_nano

    @staticmethod
    def validate_service_name(service_name: Optional[str]) -> str:
        if not service_name or not service_name.strip():
            raise PayloadValidationError("Service name cannot be empty")
        return service_name.strip()

    def validate_span_record(self, record: SpanRecord) -> None:
        if not record.tenant_id or not record.tenant_id.strip():
            raise PayloadValidationError("tenant_id cannot be empty")
        if not record.trace_id or len(record.trace_id) != 32 or record.trace_id == "0" * 32:
            raise PayloadValidationError("Invalid trace_id in SpanRecord")
        if not record.span_id or len(record.span_id) != 16 or record.span_id == "0" * 16:
            raise PayloadValidationError("Invalid span_id in SpanRecord")
        if not record.service_name or not record.service_name.strip():
            raise PayloadValidationError("Service name cannot be empty")
        if record.start_time_unix_nano <= 0:
            raise PayloadValidationError("start_time_unix_nano must be positive")
        if record.end_time_unix_nano < record.start_time_unix_nano:
            raise PayloadValidationError("end_time_unix_nano must be >= start_time_unix_nano")
