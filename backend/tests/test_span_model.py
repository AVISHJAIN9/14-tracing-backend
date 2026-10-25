import pytest
from tracelib.core.context import TraceContext, TraceFlags
from tracelib.core.ids import generate_trace_id, generate_span_id
from tracelib.core.span import Span

def test_root_span_creation():
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    context = TraceContext(trace_id=trace_id, span_id=span_id, trace_flags=TraceFlags.SAMPLED)
    
    span = Span(name="root_operation", context=context, parent_span_id=None)
    assert span.name == "root_operation"
    assert span.context.trace_id == trace_id
    assert span.context.span_id == span_id
    assert span.parent_span_id is None
    assert span.is_root is True

def test_child_span_creation_from_parent():
    trace_id = generate_trace_id()
    parent_span_id = generate_span_id()
    parent_ctx = TraceContext(trace_id=trace_id, span_id=parent_span_id, trace_flags=TraceFlags.SAMPLED)
    parent_span = Span(name="parent_op", context=parent_ctx)

    child_span = parent_span.create_child(name="child_op")
    assert child_span.name == "child_op"
    assert child_span.context.trace_id == trace_id
    assert child_span.context.span_id != parent_span_id
    assert child_span.parent_span_id == parent_span_id
    assert child_span.is_root is False
    assert child_span.context.is_sampled == parent_ctx.is_sampled

def test_grandchild_hierarchy():
    root = Span.start_root(name="root")
    child = root.create_child(name="child")
    grandchild = child.create_child(name="grandchild")

    assert root.is_root is True
    assert child.parent_span_id == root.context.span_id
    assert grandchild.parent_span_id == child.context.span_id
    assert root.context.trace_id == child.context.trace_id == grandchild.context.trace_id
    assert len({root.context.span_id, child.context.span_id, grandchild.context.span_id}) == 3

def test_reject_invalid_parent_span_id():
    ctx = TraceContext(trace_id=generate_trace_id(), span_id=generate_span_id())
    with pytest.raises(ValueError, match="invalid parent_span_id"):
        Span(name="test", context=ctx, parent_span_id="invalid_id")
