"""
tracelib.core.context — TraceContext Model and TraceFlags
Compliant with W3C Trace Context specifications.
"""

import re
from dataclasses import dataclass
from enum import IntFlag
from typing import Optional

HEX_CHARS = set("0123456789abcdefABCDEF")

class TraceFlags(IntFlag):
    NONE = 0x00
    SAMPLED = 0x01

def format_trace_flags(flags: int) -> str:
    """Format 8-bit trace flags integer into 2-character lowercase hex string."""
    if not isinstance(flags, int) or isinstance(flags, bool):
        raise TypeError("trace_flags must be an integer")
    if not (0 <= flags <= 255):
        raise ValueError("trace_flags must be an integer between 0 and 255")
    return f"{flags:02x}"

def parse_trace_flags(hex_str: str) -> int:
    """Parse 2-character hex string into 8-bit trace flags integer."""
    if not isinstance(hex_str, str):
        raise TypeError("trace_flags must be a string")
    clean = hex_str.strip()
    if len(clean) != 2:
        raise ValueError("trace_flags hex must be exactly 2 characters")
    if not all(c in HEX_CHARS for c in clean):
        raise ValueError(f"invalid hex in trace_flags: '{hex_str}'")
    return int(clean, 16)

@dataclass(frozen=True)
class TraceContext:
    """
    Immutable representation of trace propagation context.
    trace_id: 16-byte hex (32 characters)
    span_id: 8-byte hex (16 characters)
    trace_flags: 8-bit integer
    """
    trace_id: str
    span_id: str
    trace_flags: int = TraceFlags.NONE
    trace_state: Optional[str] = None
    is_remote: bool = False

    def __post_init__(self):
        if not isinstance(self.trace_id, str):
            raise TypeError("trace_id must be a string")
        if not isinstance(self.span_id, str):
            raise TypeError("span_id must be a string")

        clean_trace_id = self.trace_id.strip().lower()
        clean_span_id = self.span_id.strip().lower()

        if len(clean_trace_id) != 32 or not all(c in HEX_CHARS for c in clean_trace_id):
            raise ValueError(f"trace_id must be 32 hex characters: got '{self.trace_id}'")
        if clean_trace_id == "0" * 32:
            raise ValueError("all-zero trace_id is invalid")

        if len(clean_span_id) != 16 or not all(c in HEX_CHARS for c in clean_span_id):
            raise ValueError(f"span_id must be 16 hex characters: got '{self.span_id}'")
        if clean_span_id == "0" * 16:
            raise ValueError("all-zero span_id is invalid")

        if not isinstance(self.trace_flags, int) or not (0 <= self.trace_flags <= 255):
            raise ValueError("trace_flags must be an integer between 0 and 255")

        # Set frozen fields using object.__setattr__
        object.__setattr__(self, "trace_id", clean_trace_id)
        object.__setattr__(self, "span_id", clean_span_id)

    @property
    def is_valid(self) -> bool:
        return (
            len(self.trace_id) == 32
            and self.trace_id != "0" * 32
            and len(self.span_id) == 16
            and self.span_id != "0" * 16
        )

    @property
    def is_sampled(self) -> bool:
        return bool(self.trace_flags & TraceFlags.SAMPLED)

    def to_traceparent(self) -> str:
        flags_hex = f"{self.trace_flags:02x}"
        return f"00-{self.trace_id}-{self.span_id}-{flags_hex}"
