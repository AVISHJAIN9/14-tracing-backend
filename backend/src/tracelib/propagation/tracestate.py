"""
tracelib.propagation.tracestate — W3C tracestate Header Parsing.
Compliant with W3C Trace Context Specification.
"""

from typing import Any, Iterable, List, Optional
from tracelib.core.state import TraceState

def parse_tracestate_header(header_val: Any) -> TraceState:
    """
    Parse a single W3C tracestate header string into a TraceState instance.
    Malformed members are ignored gracefully per W3C specification.
    Duplicate keys keep the first appearance. Max 32 entries.
    """
    if not isinstance(header_val, str):
        return TraceState()
    return TraceState.from_header(header_val)

def parse_tracestate_headers(headers: Any) -> TraceState:
    """
    Parse multiple W3C tracestate header lines into a single TraceState instance.
    """
    if not headers or not isinstance(headers, Iterable) or isinstance(headers, (str, bytes)):
        return TraceState()

    valid_lines: List[str] = []
    for line in headers:
        if isinstance(line, str) and line.strip():
            valid_lines.append(line.strip())

    if not valid_lines:
        return TraceState()

    combined = ",".join(valid_lines)
    return parse_tracestate_header(combined)
