"""
backend/tests/test_missing_parent_handling.py
Comprehensive test suite for TRC-027: Missing parent handling in context extraction and span creation.
"""

import pytest
from tracelib.propagation.carrier import start_span_from_carrier

def test_missing_parent_starts_fresh_root_span():
    span, baggage = start_span_from_carrier({}, name="root-request")
    assert span is not None
    assert span.name == "root-request"
    assert span.parent_id is None
    assert span.is_root is True
    assert len(span.context.trace_id) == 32
    assert len(span.context.span_id) == 16
    assert span.context.is_remote is False
    assert baggage is None

def test_missing_parent_with_baggage_preserves_baggage():
    carrier = {"baggage": "tenant=enterprise,env=prod"}
    span, baggage = start_span_from_carrier(carrier, name="request-with-baggage")
    assert span is not None
    assert span.parent_id is None
    assert span.is_root is True
    assert baggage is not None
    assert baggage.get("tenant") == "enterprise"
    assert baggage.get("env") == "prod"

def test_missing_parent_generates_unique_trace_and_span_ids():
    span1, _ = start_span_from_carrier({}, name="span1")
    span2, _ = start_span_from_carrier({}, name="span2")
    assert span1.context.trace_id != span2.context.trace_id
    assert span1.context.span_id != span2.context.span_id

def test_missing_parent_handles_none_carrier():
    span, baggage = start_span_from_carrier(None, name="none-carrier-span")
    assert span is not None
    assert span.is_root is True
    assert span.parent_id is None
    assert baggage is None

def test_existing_parent_creates_child_not_root():
    carrier = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "rojo=1"
    }
    span, _ = start_span_from_carrier(carrier, name="child-request")
    assert span is not None
    assert span.is_root is False
    assert span.context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert span.parent_id == "00f067aa0ba902b7"
    assert span.context.trace_state == "rojo=1"
