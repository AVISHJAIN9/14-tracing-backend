import pytest
from tracelib.core.span import Span

def test_span_duration_active_span():
    span = Span.start_root(name="active_span")
    assert span.duration_nano is None
    assert span.duration_ms is None

def test_span_duration_ended_span():
    start_time = 1_700_000_000_000_000_000
    end_time = 1_700_000_000_500_000_000 # 500ms
    span = Span.start_root(name="calc_duration", start_time_unix_nano=start_time)
    span.end(end_time_unix_nano=end_time)

    assert span.duration_nano == 500_000_000
    assert span.duration_ms == 500.0

def test_span_duration_zero_duration():
    time_stamp = 1_700_000_000_000_000_000
    span = Span.start_root(name="zero_duration", start_time_unix_nano=time_stamp)
    span.end(end_time_unix_nano=time_stamp)

    assert span.duration_nano == 0
    assert span.duration_ms == 0.0

def test_span_duration_nanosecond_precision():
    start_time = 1_700_000_000_000_000_000
    end_time = 1_700_000_000_000_000_123 # 123 ns
    span = Span.start_root(name="nano_precision", start_time_unix_nano=start_time)
    span.end(end_time_unix_nano=end_time)

    assert span.duration_nano == 123
    assert span.duration_ms == 0.000123
