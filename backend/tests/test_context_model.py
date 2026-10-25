import pytest
import re
from tracelib.core.context import TraceContext, TraceFlags

def test_trace_context_valid_creation():
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED,
        is_remote=False
    )
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"
    assert ctx.trace_flags == 1
    assert ctx.is_sampled is True
    assert ctx.is_valid is True

def test_trace_context_rejects_invalid_trace_id_length():
    with pytest.raises(ValueError, match="trace_id must be 32 hex characters"):
        TraceContext(trace_id="short", span_id="00f067aa0ba902b7")

def test_trace_context_rejects_all_zero_trace_id():
    with pytest.raises(ValueError, match="all-zero trace_id is invalid"):
        TraceContext(trace_id="0" * 32, span_id="00f067aa0ba902b7")

def test_trace_context_rejects_invalid_span_id_length():
    with pytest.raises(ValueError, match="span_id must be 16 hex characters"):
        TraceContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="123")

def test_trace_context_rejects_all_zero_span_id():
    with pytest.raises(ValueError, match="all-zero span_id is invalid"):
        TraceContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="0" * 16)

def test_trace_context_normalizes_to_lowercase():
    ctx = TraceContext(
        trace_id="4BF92F3577B34DA6A3CE929D0E0E4736",
        span_id="00F067AA0BA902B7"
    )
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"

def test_trace_context_flags_boundaries():
    with pytest.raises(ValueError, match="trace_flags must be an integer between 0 and 255"):
        TraceContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            trace_flags=256
        )

def test_trace_context_immutability():
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7"
    )
    with pytest.raises((TypeError, AttributeError)):
        ctx.trace_id = "new_id"
