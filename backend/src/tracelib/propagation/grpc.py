"""
tracelib.propagation.grpc — gRPC Metadata Context and Baggage Propagation.
Supports gRPC client and server metadata structures (sequences of tuples or dicts).
"""

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
from tracelib.core.context import TraceContext
from tracelib.propagation.baggage import Baggage, W3CBaggagePropagator
from tracelib.propagation.w3c import W3CTraceContextPropagator, TRACEPARENT_HEADER, TRACESTATE_HEADER

BAGGAGE_HEADER = "baggage"

def normalize_grpc_metadata(carrier: Any) -> Dict[str, str]:
    """
    Normalize gRPC metadata carrier (sequence of tuples or mapping)
    into a lowercase string dictionary.
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

class GrpcMetadataPropagator:
    """
    Propagates W3C Trace Context and Baggage across gRPC metadata.
    """

    def __init__(self):
        self._w3c_trace = W3CTraceContextPropagator()
        self._w3c_baggage = W3CBaggagePropagator()

    def inject(
        self,
        carrier: List[Tuple[str, str]],
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
    ) -> None:
        """Inject context and baggage into a gRPC metadata tuple list."""
        if context is not None and context.is_valid:
            carrier.append((TRACEPARENT_HEADER, context.to_traceparent()))
            if context.trace_state:
                carrier.append((TRACESTATE_HEADER, context.trace_state))

        if baggage is not None and len(baggage) > 0:
            header_str = baggage.to_header()
            if header_str:
                carrier.append((BAGGAGE_HEADER, header_str))

    def inject_dict(
        self,
        carrier: MutableMapping[str, str],
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
    ) -> None:
        """Inject context and baggage into a gRPC metadata dictionary."""
        if context is not None:
            self._w3c_trace.inject(context, carrier)
        if baggage is not None:
            self._w3c_baggage.inject(baggage, carrier)

    def extract(
        self,
        carrier: Any,
    ) -> Tuple[Optional[TraceContext], Optional[Baggage]]:
        """
        Extract TraceContext and Baggage from gRPC metadata carrier.
        Returns (TraceContext or None, Baggage or None).
        """
        normalized = normalize_grpc_metadata(carrier)
        if not normalized:
            return None, None

        ctx = self._w3c_trace.extract(normalized)
        bag = self._w3c_baggage.extract(normalized)

        return ctx, bag
