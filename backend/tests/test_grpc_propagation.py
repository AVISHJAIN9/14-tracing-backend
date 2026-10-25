"""
backend/tests/test_grpc_propagation.py
Comprehensive test suite for TRC-020: gRPC metadata context propagation.
"""

import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.propagation.baggage import Baggage
from tracelib.propagation.grpc import GrpcMetadataPropagator

def test_grpc_propagation_metadata_tuples():
    propagator = GrpcMetadataPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED,
        trace_state="rojo=123"
    )
    bag = Baggage().set("client", "mobile-app")

    metadata: list = [("content-type", "application/grpc")]
    propagator.inject(metadata, context=ctx, baggage=bag)

    assert any(k == "traceparent" and v == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01" for k, v in metadata)
    assert any(k == "tracestate" and v == "rojo=123" for k, v in metadata)
    assert any(k == "baggage" and v == "client=mobile-app" for k, v in metadata)

    extracted_ctx, extracted_bag = propagator.extract(metadata)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_ctx.span_id == "00f067aa0ba902b7"
    assert extracted_ctx.is_sampled is True
    assert extracted_ctx.trace_state == "rojo=123"
    assert extracted_bag is not None
    assert extracted_bag.get("client") == "mobile-app"

def test_grpc_propagation_metadata_dict():
    propagator = GrpcMetadataPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.NONE
    )
    meta_dict = {}
    propagator.inject_dict(meta_dict, context=ctx)
    assert meta_dict["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"

    extracted_ctx, extracted_bag = propagator.extract(meta_dict)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_ctx.is_sampled is False
    assert extracted_bag is None

def test_grpc_propagation_case_insensitivity():
    propagator = GrpcMetadataPropagator()
    metadata = [
        ("TraceParent", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
        ("TraceState", "congo=test"),
        ("Baggage", "tenant=tenant-a")
    ]
    ctx, bag = propagator.extract(metadata)
    assert ctx is not None
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.trace_state == "congo=test"
    assert bag is not None
    assert bag.get("tenant") == "tenant-a"

def test_grpc_propagation_binary_or_empty_metadata():
    propagator = GrpcMetadataPropagator()
    # Empty
    ctx, bag = propagator.extract([])
    assert ctx is None
    assert bag is None

    # Binary tuples with bytes values
    raw_meta = [
        ("traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
        ("custom-bin", b"\x01\x02\x03")
    ]
    extracted_ctx, _ = propagator.extract(raw_meta)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
