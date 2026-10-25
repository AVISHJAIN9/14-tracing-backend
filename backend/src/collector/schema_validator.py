"""
OpenTelemetry 1.x Schema Compliance Validator.
Validates OTLP schema URLs, attribute key lengths, typing, and semantic conventions.
"""

from typing import Any, Optional

class SchemaValidationError(Exception):
    """Raised when an ingested span payload violates OpenTelemetry schema rules."""
    pass

class OtlpSchemaValidator:
    ALLOWED_PREFIXES = (
        "https://opentelemetry.io/schemas/",
        "http://opentelemetry.io/schemas/",
    )

    def validate_schema_url(self, schema_url: Optional[str]) -> bool:
        if not schema_url:
            return True
        if not any(schema_url.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
            raise SchemaValidationError(f"Unsupported or malformed schema_url: {schema_url}")
        return True

    def validate_attribute(self, key: str, value: Any) -> bool:
        if not key or not isinstance(key, str) or not key.strip():
            raise SchemaValidationError("Attribute key cannot be empty")
        if len(key) > 128:
            raise SchemaValidationError(f"Attribute key exceeds maximum length of 128: {len(key)}")

        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, (str, int, float, bool)):
                    raise SchemaValidationError(
                        f"Unsupported array element type: {type(item).__name__}"
                    )
            return True

        raise SchemaValidationError(f"Unsupported attribute value type: {type(value).__name__}")
