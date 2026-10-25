"""
tracelib.core.links — Span Link model.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from tracelib.core.context import TraceContext

@dataclass(frozen=True)
class SpanLink:
    """Represents a link to another Span via its TraceContext."""
    context: TraceContext
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.context, TraceContext):
            raise TypeError("context must be a TraceContext")
        if not isinstance(self.attributes, dict):
            raise TypeError("attributes must be a dict")
        object.__setattr__(self, "attributes", dict(self.attributes))
