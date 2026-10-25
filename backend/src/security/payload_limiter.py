"""
Payload size and cardinality limit enforcement service.
Guards collector and database against OOM and denial-of-service by enforcing
strict byte limits on request bodies, attribute count, string lengths, and event/link lists.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

class PayloadTooLargeError(Exception):
    pass

@dataclass(frozen=True)
class PayloadLimitsConfig:
    max_payload_bytes: int = 4 * 1024 * 1024       # 4 MB max HTTP / gRPC request body
    max_attributes_count: int = 128                # 128 attributes per span
    max_attribute_string_length: int = 4096        # 4 KB per string attribute
    max_events_count: int = 128                    # 128 events per span
    max_links_count: int = 128                     # 128 links per span

class PayloadLimiter:
    def __init__(self, config: PayloadLimitsConfig = PayloadLimitsConfig()):
        self.config = config

    def validate_request_bytes(self, payload_bytes: bytes) -> None:
        """
        Validate total request body byte length.
        """
        size = len(payload_bytes)
        if size > self.config.max_payload_bytes:
            raise PayloadTooLargeError(
                f"Payload size {size} bytes exceeds maximum allowed limit {self.config.max_payload_bytes} bytes"
            )

    def _truncate_string(self, text: str) -> str:
        if len(text.encode("utf-8")) > self.config.max_attribute_string_length:
            # Safely truncate to limit with truncation marker
            truncated = text[:self.config.max_attribute_string_length - 14] + "...[TRUNCATED]"
            return truncated
        return text

    def sanitize_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce max attribute count and truncate string attribute values exceeding max length.
        """
        if not attributes:
            return {}

        sanitized: Dict[str, Any] = {}
        for idx, (k, v) in enumerate(attributes.items()):
            if idx >= self.config.max_attributes_count:
                break
            if isinstance(v, str):
                sanitized[k] = self._truncate_string(v)
            elif isinstance(v, dict):
                sanitized[k] = self.sanitize_attributes(v)
            else:
                sanitized[k] = v

        return sanitized

    def sanitize_events(self, events: List[Any]) -> List[Any]:
        """
        Enforce max events count per span.
        """
        if not events:
            return []
        return events[:self.config.max_events_count]

    def sanitize_links(self, links: List[Any]) -> List[Any]:
        """
        Enforce max links count per span.
        """
        if not links:
            return []
        return links[:self.config.max_links_count]

    def sanitize_span_payload(
        self,
        attributes: Dict[str, Any],
        events: List[Any],
        links: List[Any]
    ) -> Tuple[Dict[str, Any], List[Any], List[Any]]:
        return (
            self.sanitize_attributes(attributes),
            self.sanitize_events(events),
            self.sanitize_links(links)
        )
