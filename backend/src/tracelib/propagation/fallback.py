"""
tracelib.propagation.fallback — Robust Fallback Context Handling.
Ensures that missing or invalid trace context always starts a new root trace and never crashes.
"""

from typing import Any, Optional
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.ids import generate_trace_id, generate_span_id
from tracelib.propagation.extract import extract_context
from tracelib.propagation.w3c import default_getter, GetterFunc

def extract_or_create_root(
    carrier: Any,
    getter: GetterFunc = default_getter,
    default_sampled: bool = True,
) -> TraceContext:
    """
    Extract a valid TraceContext from carrier.
    If the carrier is None, missing traceparent, or contains malformed/invalid IDs,
    gracefully starts and returns a NEW root TraceContext with fresh CSPRNG IDs.
    Guaranteed never to raise an unhandled exception.
    """
    try:
        if carrier is not None:
            extracted = extract_context(carrier, getter=getter)
            if (
                extracted is not None
                and extracted.trace_context is not None
                and extracted.trace_context.is_valid
            ):
                return extracted.trace_context
    except Exception:
        pass

    flags = TraceFlags.SAMPLED if default_sampled else TraceFlags.NONE
    return TraceContext(
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        trace_flags=flags,
        is_remote=False,
    )
