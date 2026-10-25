"""
tracelib.propagation.w3c — W3C Trace Context Propagator
Compliant with W3C Trace Context Recommendation (https://www.w3.org/TR/trace-context/).
"""

from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Tuple
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.state import TraceState

TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"
HEX_CHARS = set("0123456789abcdefABCDEF")

GetterFunc = Callable[[Any, str], Optional[str]]
SetterFunc = Callable[[Any, str, str], None]

def default_getter(carrier: Any, key: str) -> Optional[str]:
    """Extract key from dictionary, mapping, or sequence of tuples case-insensitively."""
    if carrier is None:
        return None
    key_lower = key.lower()
    if isinstance(carrier, Mapping):
        for k, v in carrier.items():
            if str(k).lower() == key_lower:
                if v is None:
                    return None
                return v.decode("latin-1") if isinstance(v, bytes) else str(v)
    elif isinstance(carrier, (list, tuple)):
        for item in carrier:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                k, v = item
                key_str = k.decode("latin-1") if isinstance(k, bytes) else str(k)
                if key_str.lower() == key_lower:
                    if v is None:
                        return None
                    return v.decode("latin-1") if isinstance(v, bytes) else str(v)
    return None

def default_setter(carrier: Any, key: str, value: str) -> None:
    """Set key-value in mutable mapping."""
    if isinstance(carrier, MutableMapping):
        carrier[key] = value

def parse_traceparent(header_val: str) -> Optional[Tuple[str, str, int]]:
    """
    Parse a W3C traceparent header value.
    Returns (trace_id, parent_id, trace_flags) or None if invalid.
    """
    if not isinstance(header_val, str):
        return None
    clean = header_val.strip()
    parts = clean.split("-")
    if len(parts) < 4:
        return None

    version = parts[0].lower()
    # version ff is invalid per W3C specification
    if version == "ff":
        return None
    if len(version) != 2 or not all(c in HEX_CHARS for c in version):
        return None

    # Version 00 must have exactly 4 parts
    if version == "00" and len(parts) != 4:
        return None

    trace_id = parts[1].lower()
    parent_id = parts[2].lower()
    flags_hex = parts[3].lower()

    if len(trace_id) != 32 or not all(c in HEX_CHARS for c in trace_id):
        return None
    if trace_id == "0" * 32:
        return None

    if len(parent_id) != 16 or not all(c in HEX_CHARS for c in parent_id):
        return None
    if parent_id == "0" * 16:
        return None

    if len(flags_hex) != 2 or not all(c in HEX_CHARS for c in flags_hex):
        return None

    try:
        flags = int(flags_hex, 16)
    except ValueError:
        return None

    return (trace_id, parent_id, flags)

class W3CTraceContextPropagator:
    """
    Propagator for W3C Trace Context (traceparent and tracestate headers).
    """

    def inject(
        self,
        context: TraceContext,
        carrier: MutableMapping[str, str],
        setter: SetterFunc = default_setter,
    ) -> None:
        """Inject TraceContext into carrier."""
        if context is None or not context.is_valid:
            return

        traceparent = context.to_traceparent()
        setter(carrier, TRACEPARENT_HEADER, traceparent)

        if context.trace_state:
            setter(carrier, TRACESTATE_HEADER, context.trace_state)

    def extract(
        self,
        carrier: Any,
        getter: GetterFunc = default_getter,
    ) -> Optional[TraceContext]:
        """Extract TraceContext from carrier."""
        tp_header = getter(carrier, TRACEPARENT_HEADER)
        if not tp_header:
            return None

        parsed = parse_traceparent(tp_header)
        if parsed is None:
            return None

        trace_id, parent_id, trace_flags = parsed

        ts_header = getter(carrier, TRACESTATE_HEADER)
        trace_state = None
        if ts_header:
            try:
                # Validate tracestate via TraceState parser
                state = TraceState.from_header(ts_header)
                if len(state) > 0:
                    trace_state = state.to_header()
            except Exception:
                trace_state = None

        return TraceContext(
            trace_id=trace_id,
            span_id=parent_id,
            trace_flags=trace_flags,
            trace_state=trace_state,
            is_remote=True,
        )
