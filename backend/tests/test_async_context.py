"""
backend/tests/test_async_context.py
Comprehensive test suite for TRC-022: Async contextvars propagation.
"""

import asyncio
import pytest
from tracelib.core.span import Span
from tracelib.propagation.async_context import (
    attach_span,
    detach_span,
    get_current_span,
    use_span,
)

def test_async_context_basic():
    assert get_current_span() is None
    span = Span.start_root(name="root-sync")

    token = attach_span(span)
    assert get_current_span() is span

    detach_span(token)
    assert get_current_span() is None

def test_async_context_use_span_sync():
    span1 = Span.start_root(name="span-1")
    span2 = Span.start_root(name="span-2")

    with use_span(span1):
        assert get_current_span() is span1
        with use_span(span2):
            assert get_current_span() is span2
        assert get_current_span() is span1

    assert get_current_span() is None

@pytest.mark.asyncio
async def test_async_context_use_span_async():
    span = Span.start_root(name="async-root")
    assert get_current_span() is None

    async with use_span(span):
        assert get_current_span() is span
        # Yield to event loop
        await asyncio.sleep(0.001)
        assert get_current_span() is span

    assert get_current_span() is None

@pytest.mark.asyncio
async def test_async_context_concurrent_tasks_isolation():
    async def worker(name: str):
        span = Span.start_root(name=name)
        async with use_span(span):
            for _ in range(3):
                assert get_current_span() is span
                assert get_current_span().name == name
                await asyncio.sleep(0.001)
        return name

    results = await asyncio.gather(
        worker("task-1"),
        worker("task-2"),
        worker("task-3"),
        worker("task-4")
    )
    assert set(results) == {"task-1", "task-2", "task-3", "task-4"}
    assert get_current_span() is None
