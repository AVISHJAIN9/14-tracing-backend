"""
tracelib.propagation.websocket — WebSocket Handshake and Frame Context Propagation.
Supports WebSocket handshake headers and JSON message envelope propagation.
"""

from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple
from tracelib.core.context import TraceContext
from tracelib.propagation.baggage import Baggage, W3CBaggagePropagator
from tracelib.propagation.http import HttpHeaderPropagator
from tracelib.propagation.w3c import W3CTraceContextPropagator, TRACEPARENT_HEADER, TRACESTATE_HEADER

BAGGAGE_HEADER = "baggage"
DEFAULT_ENVELOPE_KEY = "_trace"

class WebSocketPropagator:
    """
    Propagates tracing context and baggage across WebSocket connections:
    1. During connection establishment via HTTP Upgrade handshake headers.
    2. During active communication via JSON frame/message metadata envelopes.
    """

    def __init__(self):
        self._http = HttpHeaderPropagator()
        self._w3c_trace = W3CTraceContextPropagator()
        self._w3c_baggage = W3CBaggagePropagator()

    def inject_handshake(
        self,
        headers: MutableMapping[str, str],
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
    ) -> None:
        """Inject context into WebSocket upgrade handshake headers."""
        self._http.inject(headers, context=context, baggage=baggage)

    def extract_handshake(
        self,
        headers: Any,
    ) -> Tuple[Optional[TraceContext], Optional[Baggage]]:
        """Extract context from WebSocket upgrade handshake headers."""
        return self._http.extract(headers)

    def inject_message(
        self,
        message: Dict[str, Any],
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
        envelope_key: str = DEFAULT_ENVELOPE_KEY,
    ) -> Dict[str, Any]:
        """
        Inject context into a WebSocket JSON message envelope.
        Returns a new copy of the message dictionary.
        """
        if not isinstance(message, dict):
            raise TypeError("WebSocket message must be a dictionary")

        copy_msg = dict(message)
        envelope: Dict[str, str] = {}

        if context is not None and context.is_valid:
            envelope[TRACEPARENT_HEADER] = context.to_traceparent()
            if context.trace_state:
                envelope[TRACESTATE_HEADER] = context.trace_state

        if baggage is not None and len(baggage) > 0:
            header_str = baggage.to_header()
            if header_str:
                envelope[BAGGAGE_HEADER] = header_str

        if envelope:
            copy_msg[envelope_key] = envelope

        return copy_msg

    def extract_message(
        self,
        message: Any,
        envelope_key: str = DEFAULT_ENVELOPE_KEY,
    ) -> Tuple[Optional[TraceContext], Optional[Baggage]]:
        """
        Extract TraceContext and Baggage from a WebSocket JSON message envelope.
        Returns (TraceContext or None, Baggage or None).
        """
        if not isinstance(message, dict):
            return None, None

        envelope = message.get(envelope_key)
        if not isinstance(envelope, Mapping):
            return None, None

        ctx = self._w3c_trace.extract(envelope)
        bag = self._w3c_baggage.extract(envelope)
        return ctx, bag
