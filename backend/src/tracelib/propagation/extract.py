"""
tracelib.propagation.extract — Generic Context Extractor.
Extracts W3C Trace Context and Baggage, with B3 single-header fallback.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.propagation.baggage import Baggage, W3CBaggagePropagator
from tracelib.propagation.w3c import W3CTraceContextPropagator, default_getter, GetterFunc

HEX_CHARS = set("0123456789abcdefABCDEF")

@dataclass(frozen=True)
class ExtractedContext:
    trace_context: Optional[TraceContext] = None
    baggage: Optional[Baggage] = None

class DictGetter:
    """Case-insensitive getter for mappings."""
    @staticmethod
    def get(carrier: Any, key: str) -> Optional[str]:
        return default_getter(carrier, key)

def _parse_b3_single(b3_header: str) -> Optional[TraceContext]:
    """Parse B3 single header format: {TraceId}-{SpanId}-{SamplingState}"""
    if not isinstance(b3_header, str):
        return None
    clean = b3_header.strip()
    parts = clean.split("-")
    if len(parts) < 2:
        return None

    trace_id = parts[0].lower()
    span_id = parts[1].lower()

    # B3 allows 16-hex or 32-hex trace_id; pad 16-hex to 32-hex
    if len(trace_id) == 16 and all(c in HEX_CHARS for c in trace_id):
        trace_id = "0" * 16 + trace_id
    elif len(trace_id) != 32 or not all(c in HEX_CHARS for c in trace_id):
        return None

    if trace_id == "0" * 32:
        return None

    if len(span_id) != 16 or not all(c in HEX_CHARS for c in span_id):
        return None
    if span_id == "0" * 16:
        return None

    flags = TraceFlags.NONE
    if len(parts) >= 3:
        sampling = parts[2].lower()
        if sampling in ("1", "d", "true"):
            flags = TraceFlags.SAMPLED

    return TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        trace_flags=flags,
        is_remote=True,
    )

class ContextExtractor:
    """Generic context extractor combining W3C and B3 formats."""

    def __init__(self):
        self._w3c_trace = W3CTraceContextPropagator()
        self._w3c_baggage = W3CBaggagePropagator()

    def extract(
        self,
        carrier: Any,
        getter: GetterFunc = default_getter,
    ) -> Optional[ExtractedContext]:
        if carrier is None:
            return None

        # 1. Try W3C Trace Context
        trace_ctx = self._w3c_trace.extract(carrier, getter=getter)

        # 2. Fallback to B3 single header if W3C is missing
        if trace_ctx is None:
            b3_raw = getter(carrier, "b3")
            if b3_raw:
                trace_ctx = _parse_b3_single(b3_raw)

        # 3. Extract Baggage
        bag = self._w3c_baggage.extract(carrier, getter=getter)

        if trace_ctx is None and bag is None:
            return None

        return ExtractedContext(trace_context=trace_ctx, baggage=bag)

_DEFAULT_EXTRACTOR = ContextExtractor()

def extract_context(
    carrier: Any,
    getter: GetterFunc = default_getter,
) -> Optional[ExtractedContext]:
    """Convenience function to extract context from any carrier."""
    return _DEFAULT_EXTRACTOR.extract(carrier, getter=getter)
