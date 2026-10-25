"""
backend/tests/test_http_propagation.py
Comprehensive test suite for TRC-019: HTTP header context propagation.
"""

import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.propagation.baggage import Baggage
from tracelib.propagation.http import HttpHeaderPropagator

def test_http_propagation_dict_carrier():
    propagator = HttpHeaderPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED,
        trace_state="rojo=123"
    )
    bag = Baggage().set("tenant", "acme-corp")

    headers = {}
    propagator.inject(headers, context=ctx, baggage=bag)

    assert headers["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert headers["tracestate"] == "rojo=123"
    assert headers["baggage"] == "tenant=acme-corp"

    extracted_ctx, extracted_bag = propagator.extract(headers)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_ctx.span_id == "00f067aa0ba902b7"
    assert extracted_ctx.is_sampled is True
    assert extracted_ctx.trace_state == "rojo=123"
    assert extracted_bag is not None
    assert extracted_bag.get("tenant") == "acme-corp"

def test_http_propagation_asgi_headers():
    propagator = HttpHeaderPropagator()
    raw_asgi_headers = [
        (b"host", b"api.example.com"),
        (b"traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
        (b"tracestate", b"congo=xyz"),
        (b"baggage", b"role=admin;cluster=us-east")
    ]

    extracted_ctx, extracted_bag = propagator.extract(raw_asgi_headers)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_ctx.span_id == "00f067aa0ba902b7"
    assert extracted_ctx.trace_state == "congo=xyz"
    assert extracted_bag is not None
    assert extracted_bag.get("role") == "admin"
    assert extracted_bag.get_entry("role").metadata == "cluster=us-east"

def test_http_propagation_case_insensitivity():
    propagator = HttpHeaderPropagator()
    headers = {
        "TraceParent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00",
        "TraceState": "k=v",
        "Baggage": "userId=99"
    }
    ctx, bag = propagator.extract(headers)
    assert ctx is not None
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.trace_state == "k=v"
    assert bag is not None
    assert bag.get("userId") == "99"

def test_http_propagation_missing_or_empty_headers():
    propagator = HttpHeaderPropagator()
    ctx, bag = propagator.extract({})
    assert ctx is None
    assert bag is None

    ctx2, bag2 = propagator.extract([])
    assert ctx2 is None
    assert bag2 is None

def test_http_propagation_bytes_encoding_and_decoding():
    propagator = HttpHeaderPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED
    )
    carrier: list = []
    propagator.inject_asgi(carrier, context=ctx)
    assert any(k == b"traceparent" for k, v in carrier)
    extracted_ctx, _ = propagator.extract(carrier)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
