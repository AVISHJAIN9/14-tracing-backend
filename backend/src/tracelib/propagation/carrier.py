"""
tracelib.propagation.carrier — Carrier-to-Span Activation and Missing Parent Handling.
Initializes spans from incoming carriers, cleanly starting root spans when parents are missing.
"""

from typing import Any, Optional, Tuple
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.ids import generate_span_id
from tracelib.core.span import Span
from tracelib.propagation.baggage import Baggage
from tracelib.propagation.extract import extract_context
from tracelib.propagation.w3c import default_getter, GetterFunc

def start_span_from_carrier(
    carrier: Any,
    name: str,
    getter: GetterFunc = default_getter,
) -> Tuple[Span, Optional[Baggage]]:
    """
    Extract trace context from an incoming carrier and start a corresponding Span.
    If parent context is present and valid, starts a child Span linked to that parent.
    If parent context is missing or invalid, cleanly starts a fresh root Span with parent_id=None.
    Preserves any propagated Baggage in either case.
    """
    extracted = None
    if carrier is not None:
        try:
            extracted = extract_context(carrier, getter=getter)
        except Exception:
            extracted = None

    baggage = extracted.baggage if extracted else None

    if (
        extracted is not None
        and extracted.trace_context is not None
        and extracted.trace_context.is_valid
    ):
        parent = extracted.trace_context
        # Create child span linked to extracted remote parent
        child_span_id = generate_span_id()
        child_context = TraceContext(
            trace_id=parent.trace_id,
            span_id=child_span_id,
            trace_flags=parent.trace_flags,
            trace_state=parent.trace_state,
            is_remote=False,
        )
        span = Span(
            name=name,
            context=child_context,
            parent_id=parent.span_id,
        )
        return span, baggage

    # Missing parent: cleanly start a fresh root span
    root_span = Span.start_root(name=name)
    return root_span, baggage
