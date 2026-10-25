import pytest
import time
from tracelib.core.span import Span

def test_span_end_timestamp_before_end():
    span = Span.start_root(name="active_span")
    assert span.end_time_unix_nano is None

def test_span_end_timestamp_automatic():
    span = Span.start_root(name="auto_end")
    time.sleep(0.001)
    span.end()
    assert isinstance(span.end_time_unix_nano, int)
    assert span.end_time_unix_nano >= span.start_time_unix_nano

def test_span_end_timestamp_explicit():
    start_time = 1_700_000_000_000_000_000
    end_time = 1_700_000_000_500_000_000
    span = Span.start_root(name="explicit_end", start_time_unix_nano=start_time)
    span.end(end_time_unix_nano=end_time)
    assert span.end_time_unix_nano == end_time

def test_span_end_timestamp_rejects_earlier_than_start():
    start_time = 1_700_000_000_000_000_000
    earlier_time = 1_699_999_999_999_999_999
    span = Span.start_root(name="invalid_end", start_time_unix_nano=start_time)
    with pytest.raises(ValueError, match="end_time_unix_nano must be an integer >= start_time_unix_nano"):
        span.end(end_time_unix_nano=earlier_time)

def test_span_end_timestamp_type_check():
    span = Span.start_root(name="type_check_end")
    with pytest.raises(TypeError, match="end_time_unix_nano must be an integer"):
        span.end(end_time_unix_nano="not_int")
