"""
tracelib.propagation.http — HTTP Header Context and Baggage Propagation.
Supports ASGI, WSGI, requests, httpx, and standard dictionary carriers.
"""

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from tracelib.core.context import TraceContext
from tracelib.propagation.baggage import Baggage, W3CBaggagePropagator
from tracelib.propagation.w3c import W3CTraceContextPropagator, TRACEPARENT_HEADER, TRACESTATE_HEADER

BAGGAGE_HEADER = "baggage"

def normalize_http_headers(carrier: Any) -> Dict[str, str]:
    """
    Normalize different HTTP header representations (dict, ASGI tuples, WSGI environ)
    into a lowercase string-keyed dictionary.
    """
    if carrier is None:
        return {}

    normalized: Dict[str, str] = {}

    if isinstance(carrier, Mapping):
        for k, v in carrier.items():
            if k is not None and v is not None:
                key_str = k.decode("latin-1") if isinstance(k, bytes) else str(k)
                val_str = v.decode("latin-1") if isinstance(v, bytes) else str(v)
                normalized[key_str.lower()] = val_str

    elif isinstance(carrier, Sequence) and not isinstance(carrier, (str, bytes)):
        for item in carrier:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                k, v = item
                if k is not None and v is not None:
                    key_str = k.decode("latin-1") if isinstance(k, bytes) else str(k)
                    val_str = v.decode("latin-1") if isinstance(v, bytes) else str(v)
                    normalized[key_str.lower()] = val_str

    return normalized

class HttpHeaderPropagator:
    """
    HTTP Header Propagator coordinating W3C Trace Context and Baggage propagation
    over HTTP headers across various framework conventions.
    """

    def __init__(self):
        self._w3c_trace = W3CTraceContextPropagator()
        self._w3c_baggage = W3CBaggagePropagator()

    def inject(
        self,
        carrier: MutableMapping[str, str],
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
    ) -> None:
        """Inject TraceContext and Baggage into an HTTP header dictionary."""
        if context is not None:
            self._w3c_trace.inject(context, carrier)
        if baggage is not None:
            self._w3c_baggage.inject(baggage, carrier)

    def inject_asgi(
        self,
        carrier: List[Tuple[bytes, bytes]],
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
    ) -> None:
        """Inject TraceContext and Baggage into raw ASGI byte header list."""
        if context is not None and context.is_valid:
            carrier.append((b"traceparent", context.to_traceparent().encode("ascii")))
            if context.trace_state:
                carrier.append((b"tracestate", context.trace_state.encode("ascii")))

        if baggage is not None and len(baggage) > 0:
            header_str = baggage.to_header()
            if header_str:
                carrier.append((b"baggage", header_str.encode("utf-8")))

    def extract(
        self,
        carrier: Any,
    ) -> Tuple[Optional[TraceContext], Optional[Baggage]]:
        """
        Extract TraceContext and Baggage from HTTP headers (dict or ASGI sequence).
        Returns (TraceContext or None, Baggage or None).
        """
        normalized = normalize_http_headers(carrier)
        if not normalized:
            return None, None

        ctx = self._w3c_trace.extract(normalized)
        bag = self._w3c_baggage.extract(normalized)

        return ctx, bag
