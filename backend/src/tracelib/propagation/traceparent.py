"""
tracelib.propagation.traceparent — W3C traceparent Header Parsing and Model.
Compliant with W3C Trace Context Specification.
"""

from dataclasses import dataclass
from typing import Any, Optional

HEX_CHARS = set("0123456789abcdefABCDEF")

@dataclass(frozen=True)
class Traceparent:
    version: str
    trace_id: str
    parent_id: str
    trace_flags: int

    @property
    def is_sampled(self) -> bool:
        return bool(self.trace_flags & 0x01)

    def to_header(self) -> str:
        return f"{self.version}-{self.trace_id}-{self.parent_id}-{self.trace_flags:02x}"

def parse_traceparent_header(header_val: Any) -> Optional[Traceparent]:
    """
    Parse a W3C traceparent header string.
    Format: version-trace_id-parent_id-trace_flags
    Returns Traceparent instance or None if invalid.
    """
    if not isinstance(header_val, str):
        return None

    clean = header_val.strip()
    parts = clean.split("-")
    if len(parts) < 4:
        return None

    version = parts[0].lower()
    if len(version) != 2 or not all(c in HEX_CHARS for c in version):
        return None

    # Version 'ff' is forbidden by W3C specification
    if version == "ff":
        return None

    # Version '00' forbids extra delimiter fields or extra content
    if version == "00" and len(parts) != 4:
        return None

    trace_id = parts[1].lower()
    parent_id = parts[2].lower()
    flags_hex = parts[3].lower()

    # Trace ID validation: 32 hex chars, non-zero
    if len(trace_id) != 32 or not all(c in HEX_CHARS for c in trace_id):
        return None
    if trace_id == "0" * 32:
        return None

    # Parent ID validation: 16 hex chars, non-zero
    if len(parent_id) != 16 or not all(c in HEX_CHARS for c in parent_id):
        return None
    if parent_id == "0" * 16:
        return None

    # Flags validation: exactly 2 hex chars
    if len(flags_hex) != 2 or not all(c in HEX_CHARS for c in flags_hex):
        return None

    try:
        flags = int(flags_hex, 16)
    except ValueError:
        return None

    return Traceparent(
        version=version,
        trace_id=trace_id,
        parent_id=parent_id,
        trace_flags=flags,
    )
