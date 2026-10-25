"""
backend/tests/test_w3c_trace_context.py
Tests for TRC-015: W3C Trace Context propagation and serialization.
"""

import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.state import TraceState
from tracelib.propagation.w3c import W3CTraceContextPropagator

def test_w3c_trace_context_roundtrip():
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    span_id = "00f067aa0ba902b7"
    state = TraceState.from_header("rojo=123,congo=456")
    ctx = TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        trace_flags=TraceFlags.SAMPLED,
        trace_state=state.to_header(),
        is_remote=False
    )

    propagator = W3CTraceContextPropagator()
    headers = {}
    propagator.inject(ctx, headers)

    assert headers["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert headers["tracestate"] == "rojo=123,congo=456"

    extracted_ctx = propagator.extract(headers)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == trace_id
    assert extracted_ctx.span_id == span_id
    assert extracted_ctx.trace_flags == TraceFlags.SAMPLED
    assert extracted_ctx.trace_state == "rojo=123,congo=456"
    assert extracted_ctx.is_remote is True

def test_w3c_trace_context_no_tracestate():
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
    }
    propagator = W3CTraceContextPropagator()
    extracted_ctx = propagator.extract(headers)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_ctx.span_id == "00f067aa0ba902b7"
    assert extracted_ctx.trace_flags == 0
    assert extracted_ctx.trace_state is None
    assert extracted_ctx.is_remote is True

def test_w3c_trace_context_case_insensitive_header_keys():
    headers = {
        "TraceParent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "TraceState": "congo=xyz"
    }
    propagator = W3CTraceContextPropagator()
    extracted = propagator.extract(headers)
    assert extracted is not None
    assert extracted.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted.trace_state == "congo=xyz"

def test_w3c_trace_context_missing_traceparent():
    headers = {"tracestate": "vendor=1"}
    propagator = W3CTraceContextPropagator()
    extracted = propagator.extract(headers)
    assert extracted is None

def test_w3c_trace_context_empty_carrier():
    propagator = W3CTraceContextPropagator()
    extracted = propagator.extract({})
    assert extracted is None
