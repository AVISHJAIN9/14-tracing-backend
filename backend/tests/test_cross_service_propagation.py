"""
backend/tests/test_cross_service_propagation.py
Integration test for TRC-028 (Mandatory System Scenario S14-02):
One request crosses 4 services via HTTP, gRPC and WebSocket;
Single trace maintains constant trace_id and correct parent/child links.
"""

import pytest
from tracelib.core.span import Span
from tracelib.propagation.baggage import Baggage
from tracelib.propagation.http import HttpHeaderPropagator
from tracelib.propagation.grpc import GrpcMetadataPropagator
from tracelib.propagation.websocket import WebSocketPropagator
from tracelib.propagation.carrier import start_span_from_carrier

def test_cross_service_4_hop_propagation():
    # -------------------------------------------------------------
    # 1. Service A: API Gateway (starts root span, makes HTTP call)
    # -------------------------------------------------------------
    root_span = Span.start_root(name="gateway.handle_request")
    root_baggage = Baggage().set("tenantId", "acme-123").set("userId", "usr-999")

    http_headers = {}
    http_propagator = HttpHeaderPropagator()
    http_propagator.inject(http_headers, context=root_span.context, baggage=root_baggage)
    root_span.end()

    # -------------------------------------------------------------
    # 2. Service B: Order Service (extracts HTTP, makes gRPC call)
    # -------------------------------------------------------------
    b_span, b_baggage = start_span_from_carrier(http_headers, name="order.process_order")
    assert b_span.context.trace_id == root_span.context.trace_id
    assert b_span.parent_id == root_span.context.span_id
    assert b_baggage.get("tenantId") == "acme-123"

    grpc_metadata = []
    grpc_propagator = GrpcMetadataPropagator()
    grpc_propagator.inject(grpc_metadata, context=b_span.context, baggage=b_baggage)
    b_span.end()

    # -------------------------------------------------------------
    # 3. Service C: Inventory Service (extracts gRPC, publishes WS)
    # -------------------------------------------------------------
    c_span, c_baggage = start_span_from_carrier(grpc_metadata, name="inventory.reserve_stock")
    assert c_span.context.trace_id == root_span.context.trace_id
    assert c_span.parent_id == b_span.context.span_id
    assert c_baggage.get("tenantId") == "acme-123"

    ws_message = {"event": "order_confirmed", "order_id": "ord-777"}
    ws_propagator = WebSocketPropagator()
    ws_enveloped = ws_propagator.inject_message(ws_message, context=c_span.context, baggage=c_baggage)
    c_span.end()

    # -------------------------------------------------------------
    # 4. Service D: Notification Service (receives WS frame)
    # -------------------------------------------------------------
    d_ctx, d_baggage = ws_propagator.extract_message(ws_enveloped)
    assert d_ctx is not None
    assert d_ctx.trace_id == root_span.context.trace_id
    assert d_ctx.span_id == c_span.context.span_id

    # Create consumer span
    d_span = Span.start_root(name="notification.send_email")
    # Link child to remote context
    d_child = Span(
        name="notification.dispatch",
        context=d_ctx,
        parent_id=c_span.context.span_id,
    )
    d_child.end()

    # Verify end-to-end lineage invariant
    trace_id = root_span.context.trace_id
    assert b_span.context.trace_id == trace_id
    assert c_span.context.trace_id == trace_id
    assert d_ctx.trace_id == trace_id

    # Chain of parents: root -> B -> C -> D
    assert root_span.parent_id is None
    assert b_span.parent_id == root_span.context.span_id
    assert c_span.parent_id == b_span.context.span_id
    assert d_child.parent_id == c_span.context.span_id

    # Baggage preserved across all 4 hops
    assert d_baggage.get("tenantId") == "acme-123"
    assert d_baggage.get("userId") == "usr-999"

def test_cross_service_trace_flags_propagation():
    # Verify sampled flag propagates through all carriers
    root_span = Span.start_root(name="root-sampled")
    assert root_span.context.is_sampled is True

    headers = {}
    HttpHeaderPropagator().inject(headers, context=root_span.context)

    b_span, _ = start_span_from_carrier(headers, name="hop-2")
    assert b_span.context.is_sampled is True

    meta = []
    GrpcMetadataPropagator().inject(meta, context=b_span.context)

    c_span, _ = start_span_from_carrier(meta, name="hop-3")
    assert c_span.context.is_sampled is True

    msg = WebSocketPropagator().inject_message({}, context=c_span.context)
    d_ctx, _ = WebSocketPropagator().extract_message(msg)
    assert d_ctx.is_sampled is True
