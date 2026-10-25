import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.ids import generate_trace_id, generate_span_id
from tracelib.core.span import Span, SpanLink

def test_span_links_initial():
    span = Span.start_root(name="link_test")
    assert span.links == []

def test_span_add_link():
    span = Span.start_root(name="consumer_span")
    producer_ctx = TraceContext(
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
        trace_flags=TraceFlags.SAMPLED
    )
    span.add_link(context=producer_ctx, attributes={"messaging.operation": "receive"})

    assert len(span.links) == 1
    link = span.links[0]
    assert isinstance(link, SpanLink)
    assert link.context == producer_ctx
    assert link.attributes["messaging.operation"] == "receive"

def test_span_add_link_invalid_context():
    span = Span.start_root(name="link_test")
    with pytest.raises(TypeError, match="context must be a TraceContext"):
        span.add_link(context="invalid_context")

def test_span_add_link_immutable_after_end():
    span = Span.start_root(name="link_test")
    ctx1 = TraceContext(trace_id=generate_trace_id(), span_id=generate_span_id())
    ctx2 = TraceContext(trace_id=generate_trace_id(), span_id=generate_span_id())

    span.add_link(context=ctx1)
    span.end()
    span.add_link(context=ctx2)

    assert len(span.links) == 1
    assert span.links[0].context == ctx1
