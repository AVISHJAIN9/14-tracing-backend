"""
backend/tests/test_context_extraction.py
Comprehensive test suite for TRC-024: Generic context extraction.
"""

import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.propagation.extract import extract_context, ContextExtractor, DictGetter

def test_context_extraction_w3c():
    carrier = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "rojo=123",
        "baggage": "user=bob;role=admin"
    }
    extracted = extract_context(carrier)
    assert extracted is not None
    assert extracted.trace_context is not None
    assert extracted.trace_context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted.trace_context.span_id == "00f067aa0ba902b7"
    assert extracted.trace_context.is_sampled is True
    assert extracted.trace_context.trace_state == "rojo=123"
    assert extracted.baggage is not None
    assert extracted.baggage.get("user") == "bob"

def test_context_extraction_custom_getter():
    class CustomCarrier:
        def __init__(self, data):
            self._data = data
        def read_header(self, key):
            return self._data.get(key.upper())

    carrier = CustomCarrier({
        "TRACEPARENT": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
    })
    extractor = ContextExtractor()
    extracted = extractor.extract(carrier, getter=lambda c, k: c.read_header(k))
    assert extracted is not None
    assert extracted.trace_context is not None
    assert extracted.trace_context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted.trace_context.is_sampled is False

def test_context_extraction_b3_fallback():
    # B3 single header format: {TraceId}-{SpanId}-{SamplingState}
    carrier = {
        "b3": "4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-1"
    }
    extracted = extract_context(carrier)
    assert extracted is not None
    assert extracted.trace_context is not None
    assert extracted.trace_context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted.trace_context.span_id == "00f067aa0ba902b7"
    assert extracted.trace_context.is_sampled is True

def test_context_extraction_prefers_w3c_over_b3():
    carrier = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "b3": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-cccccccccccccccc-0"
    }
    extracted = extract_context(carrier)
    assert extracted is not None
    assert extracted.trace_context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

def test_context_extraction_empty_carrier():
    extracted = extract_context({})
    assert extracted is None

    extracted2 = extract_context(None)
    assert extracted2 is None
