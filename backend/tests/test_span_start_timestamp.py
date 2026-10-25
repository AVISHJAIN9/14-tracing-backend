import pytest
import time
from tracelib.core.span import Span

def test_span_start_timestamp_automatic():
    before_ns = time.time_ns()
    span = Span.start_root(name="auto_start")
    after_ns = time.time_ns()

    assert isinstance(span.start_time_unix_nano, int)
    assert before_ns <= span.start_time_unix_nano <= after_ns

def test_span_start_timestamp_explicit():
    custom_time = 1_700_000_000_000_000_000
    span = Span.start_root(name="explicit_start", start_time_unix_nano=custom_time)
    assert span.start_time_unix_nano == custom_time

def test_span_start_timestamp_invalid():
    with pytest.raises(ValueError, match="start_time_unix_nano must be a positive integer"):
        Span.start_root(name="invalid_start", start_time_unix_nano=0)

    with pytest.raises(ValueError, match="start_time_unix_nano must be a positive integer"):
        Span.start_root(name="invalid_start", start_time_unix_nano=-100)

    with pytest.raises(TypeError, match="start_time_unix_nano must be an integer"):
        Span.start_root(name="invalid_start", start_time_unix_nano="not_int")
