"""
tracelib.propagation.inject — Generic Context Injector.
Injects W3C Trace Context and Baggage, with optional B3 format support.
"""

from typing import Any, MutableMapping, Optional
from tracelib.core.context import TraceContext
from tracelib.propagation.async_context import get_current_span
from tracelib.propagation.baggage import Baggage, W3CBaggagePropagator
from tracelib.propagation.w3c import W3CTraceContextPropagator, default_setter, SetterFunc

class ContextInjector:
    """Generic context injector for outgoing carriers."""

    def __init__(self, enable_b3: bool = False):
        self._w3c_trace = W3CTraceContextPropagator()
        self._w3c_baggage = W3CBaggagePropagator()
        self.enable_b3 = enable_b3

    def inject(
        self,
        carrier: Any,
        context: Optional[TraceContext] = None,
        baggage: Optional[Baggage] = None,
        setter: SetterFunc = default_setter,
    ) -> None:
        """
        Inject TraceContext and Baggage into the carrier.
        If context is None, falls back to active Span in async/thread context.
        """
        target_context = context
        if target_context is None:
            active_span = get_current_span()
            if active_span is not None:
                target_context = active_span.context

        if target_context is not None and target_context.is_valid:
            # 1. Inject W3C Trace Context
            self._w3c_trace.inject(target_context, carrier, setter=setter)

            # 2. Optionally inject B3 single header
            if self.enable_b3:
                sample_flag = "1" if target_context.is_sampled else "0"
                b3_val = f"{target_context.trace_id}-{target_context.span_id}-{sample_flag}"
                setter(carrier, "b3", b3_val)

        # 3. Inject Baggage
        if baggage is not None:
            self._w3c_baggage.inject(baggage, carrier, setter=setter)

_DEFAULT_INJECTOR = ContextInjector(enable_b3=False)

def inject_context(
    carrier: Any,
    context: Optional[TraceContext] = None,
    baggage: Optional[Baggage] = None,
    setter: SetterFunc = default_setter,
) -> None:
    """Convenience function to inject context into any carrier."""
    _DEFAULT_INJECTOR.inject(carrier, context=context, baggage=baggage, setter=setter)
