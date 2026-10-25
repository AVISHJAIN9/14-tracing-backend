import pytest
from tracelib.core.span import Span, StatusCode, Status

def test_span_default_status():
    span = Span.start_root(name="status_test")
    assert span.status.status_code == StatusCode.UNSET
    assert span.status.description is None
    assert span.is_error is False

def test_span_set_status_ok():
    span = Span.start_root(name="status_test")
    span.set_status(StatusCode.OK)
    assert span.status.status_code == StatusCode.OK
    assert span.is_error is False

def test_span_set_status_error():
    span = Span.start_root(name="status_test")
    span.set_status(StatusCode.ERROR, description="Database connection failed")
    assert span.status.status_code == StatusCode.ERROR
    assert span.status.description == "Database connection failed"
    assert span.is_error is True

def test_span_status_immutable_after_end():
    span = Span.start_root(name="ended_span")
    span.end()
    # Setting status after end is ignored (no-op per OTel spec)
    span.set_status(StatusCode.ERROR, description="Late error")
    assert span.status.status_code == StatusCode.UNSET
