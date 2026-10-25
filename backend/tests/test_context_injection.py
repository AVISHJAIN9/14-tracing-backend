"""
backend/tests/test_context_injection.py
Comprehensive test suite for TRC-025: Generic context injection.
"""

import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.span import Span
from tracelib.propagation.async_context import use_span
from tracelib.propagation.baggage import Baggage
from tracelib.propagation.inject import inject_context, ContextInjector

def test_context_injection_explicit_context():
    carrier = {}
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED,
        trace_state="rojo=123"
    )
    bag = Baggage().set("service", "billing")

    inject_context(carrier, context=ctx, baggage=bag)
    assert carrier["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert carrier["tracestate"] == "rojo=123"
    assert carrier["baggage"] == "service=billing"

def test_context_injection_from_active_span():
    carrier = {}
    span = Span.start_root(name="active-root")
    with use_span(span):
        inject_context(carrier)

    assert "traceparent" in carrier
    assert carrier["traceparent"] == span.context.to_traceparent()

def test_context_injection_custom_setter():
    class CustomRequest:
        def __init__(self):
            self.headers = {}
        def set_header(self, key, value):
            self.headers[key.lower()] = value

    req = CustomRequest()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED
    )
    injector = ContextInjector()
    injector.inject(req, context=ctx, setter=lambda r, k, v: r.set_header(k, v))
    assert req.headers["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

def test_context_injection_b3_format():
    carrier = {}
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED
    )
    injector = ContextInjector(enable_b3=True)
    injector.inject(carrier, context=ctx)
    assert carrier["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert carrier["b3"] == "4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-1"

def test_context_injection_skips_invalid_context():
    carrier = {}
    inject_context(carrier, context=None)
    assert len(carrier) == 0
