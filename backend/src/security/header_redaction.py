"""
HTTP header redaction engine for distributed tracing attributes.
Detects and masks sensitive HTTP headers (authorization, cookies, api-keys, proxy tokens)
both in standalone header maps and embedded in OpenTelemetry span attributes (http.request.header.*).
"""

from typing import Any, Dict, Optional, Set

DEFAULT_SENSITIVE_HEADERS: Set[str] = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "x-amz-security-token",
    "x-azure-authorization"
}

class HeaderRedactor:
    def __init__(
        self,
        sensitive_headers: Optional[Set[str]] = None,
        mask: str = "[REDACTED]"
    ):
        self.sensitive_headers = {h.lower() for h in (sensitive_headers or DEFAULT_SENSITIVE_HEADERS)}
        self.mask = mask

    def is_sensitive_header(self, header_name: str) -> bool:
        clean = header_name.lower().strip()
        # Direct match or otel attribute prefix match
        if clean in self.sensitive_headers:
            return True
        for prefix in ("http.request.header.", "http.response.header.", "rpc.metadata."):
            if clean.startswith(prefix):
                suffix = clean[len(prefix):]
                if suffix in self.sensitive_headers:
                    return True
        return False

    def redact_headers_dict(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Redact a dictionary of HTTP headers.
        """
        result: Dict[str, str] = {}
        for k, v in headers.items():
            if self.is_sensitive_header(k):
                result[k] = self.mask
            else:
                result[k] = v
        return result

    def redact_span_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspect span attributes and redact any key matching sensitive header conventions.
        """
        result: Dict[str, Any] = {}
        for k, v in attributes.items():
            if self.is_sensitive_header(k):
                result[k] = self.mask
            elif isinstance(v, dict):
                result[k] = self.redact_span_attributes(v)
            else:
                result[k] = v
        return result
