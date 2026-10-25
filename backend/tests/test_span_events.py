import pytest
import time
from tracelib.core.span import Span, SpanEvent

def test_span_add_event_automatic_timestamp():
    before_ns = time.time_ns()
    span = Span.start_root(name="event_test")
    span.add_event(name="cache_miss", attributes={"cache.key": "user:123"})
    after_ns = time.time_ns()

    assert len(span.events) == 1
    event = span.events[0]
    assert isinstance(event, SpanEvent)
    assert event.name == "cache_miss"
    assert event.attributes["cache.key"] == "user:123"
    assert before_ns <= event.timestamp_unix_nano <= after_ns

def test_span_add_event_explicit_timestamp():
    ts = 1_700_000_000_123_456_789
    span = Span.start_root(name="event_test")
    span.add_event(name="dns_resolved", timestamp_unix_nano=ts)

    assert len(span.events) == 1
    assert span.events[0].name == "dns_resolved"
    assert span.events[0].timestamp_unix_nano == ts
    assert span.events[0].attributes == {}

def test_span_add_event_invalid_name():
    span = Span.start_root(name="event_test")
    with pytest.raises(TypeError, match="event name must be a string"):
        span.add_event(name=123)
    with pytest.raises(ValueError, match="event name must not be empty"):
        span.add_event(name="")

def test_span_record_exception():
    span = Span.start_root(name="exception_test")
    try:
        raise ValueError("Invalid query parameter")
    except ValueError as e:
        span.record_exception(e)

    assert len(span.events) == 1
    event = span.events[0]
    assert event.name == "exception"
    assert event.attributes["exception.type"] == "ValueError"
    assert event.attributes["exception.message"] == "Invalid query parameter"
    assert "exception.stacktrace" in event.attributes

def test_span_add_event_immutable_after_end():
    span = Span.start_root(name="event_test")
    span.add_event("event_before")
    span.end()
    span.add_event("event_after")

    assert len(span.events) == 1
    assert span.events[0].name == "event_before"
