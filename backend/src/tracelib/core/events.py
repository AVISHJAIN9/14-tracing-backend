"""
tracelib.core.events — Span Event model.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class SpanEvent:
    """Represents a timestamped event within a span."""
    name: str
    timestamp_unix_nano: int
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.name, str):
            raise TypeError("event name must be a string")
        if not self.name:
            raise ValueError("event name must not be empty")
        if not isinstance(self.timestamp_unix_nano, int) or isinstance(self.timestamp_unix_nano, bool):
            raise TypeError("timestamp_unix_nano must be an integer")
        if self.timestamp_unix_nano <= 0:
            raise ValueError("timestamp_unix_nano must be a positive integer")
        if not isinstance(self.attributes, dict):
            raise TypeError("attributes must be a dict")
        # Ensure immutable copy
        object.__setattr__(self, "attributes", dict(self.attributes))
