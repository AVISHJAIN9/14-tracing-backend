"""
backend/tests/test_websocket_propagation.py
Comprehensive test suite for TRC-021: WebSocket context propagation.
"""

import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.propagation.baggage import Baggage
from tracelib.propagation.websocket import WebSocketPropagator

def test_websocket_handshake_propagation():
    propagator = WebSocketPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED,
        trace_state="rojo=ws"
    )
    bag = Baggage().set("channel", "chat")

    handshake_headers = {"Upgrade": "websocket", "Connection": "Upgrade"}
    propagator.inject_handshake(handshake_headers, context=ctx, baggage=bag)

    assert handshake_headers["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert handshake_headers["tracestate"] == "rojo=ws"
    assert handshake_headers["baggage"] == "channel=chat"

    extracted_ctx, extracted_bag = propagator.extract_handshake(handshake_headers)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_bag is not None
    assert extracted_bag.get("channel") == "chat"

def test_websocket_json_message_envelope():
    propagator = WebSocketPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.SAMPLED
    )
    bag = Baggage().set("event", "ping")

    message = {"type": "heartbeat", "data": 123}
    enveloped = propagator.inject_message(message, context=ctx, baggage=bag)

    assert "_trace" in enveloped
    assert enveloped["_trace"]["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert enveloped["_trace"]["baggage"] == "event=ping"
    assert enveloped["type"] == "heartbeat"

    extracted_ctx, extracted_bag = propagator.extract_message(enveloped)
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extracted_bag is not None
    assert extracted_bag.get("event") == "ping"

def test_websocket_custom_envelope_key():
    propagator = WebSocketPropagator()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=TraceFlags.NONE
    )
    message = {"action": "subscribe"}
    enveloped = propagator.inject_message(message, context=ctx, envelope_key="metadata")
    assert "metadata" in enveloped
    assert "traceparent" in enveloped["metadata"]

    extracted_ctx, _ = propagator.extract_message(enveloped, envelope_key="metadata")
    assert extracted_ctx is not None
    assert extracted_ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

def test_websocket_missing_envelope_graceful():
    propagator = WebSocketPropagator()
    message = {"action": "plain_message"}
    ctx, bag = propagator.extract_message(message)
    assert ctx is None
    assert bag is None

def test_websocket_malformed_envelope_graceful():
    propagator = WebSocketPropagator()
    message1 = {"_trace": "invalid_string_not_dict"}
    ctx1, bag1 = propagator.extract_message(message1)
    assert ctx1 is None
    assert bag1 is None

    message2 = {"_trace": {"traceparent": "malformed-tp"}}
    ctx2, bag2 = propagator.extract_message(message2)
    assert ctx2 is None
    assert bag2 is None
