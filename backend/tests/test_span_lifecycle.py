import pytest
import time
from tracelib.core.span import Span

def test_span_lifecycle_states():
    span = Span.start_root(name="test_op")
    assert span.is_recording is True
    assert span.is_ended is False

    span.end()
    assert span.is_recording is False
    assert span.is_ended is True

def test_span_context_manager():
    span = Span.start_root(name="context_op")
    with span as s:
        assert s is span
        assert s.is_recording is True
    assert span.is_ended is True

def test_span_multiple_ends_idempotent():
    span = Span.start_root(name="multi_end")
    span.end()
    first_end = span.end_time_unix_nano
    time.sleep(0.001)
    span.end()
    assert span.end_time_unix_nano == first_end
