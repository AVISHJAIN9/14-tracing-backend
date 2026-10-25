"""
backend/tests/test_thread_context.py
Comprehensive test suite for TRC-023: Thread context propagation.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from tracelib.core.span import Span
from tracelib.propagation.async_context import get_current_span, use_span
from tracelib.propagation.thread_context import (
    ContextThreadPoolExecutor,
    wrap_callable_with_context,
)

def test_thread_isolation_default():
    span = Span.start_root(name="main-thread-span")
    child_span_in_thread = None

    def worker():
        nonlocal child_span_in_thread
        child_span_in_thread = get_current_span()

    with use_span(span):
        t = threading.Thread(target=worker)
        t.start()
        t.join()

    # Raw thread should not have the parent span unless explicitly propagated
    assert child_span_in_thread is None

def test_wrap_callable_with_context():
    span = Span.start_root(name="captured-span")
    observed_span = None

    def worker():
        nonlocal observed_span
        observed_span = get_current_span()

    with use_span(span):
        wrapped = wrap_callable_with_context(worker)

    t = threading.Thread(target=wrapped)
    t.start()
    t.join()

    assert observed_span is span

def test_context_thread_pool_executor_submit():
    span = Span.start_root(name="pool-span")

    def worker(val: int):
        current = get_current_span()
        return current.name if current else None, val * 2

    with use_span(span):
        with ContextThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(worker, 21)
            name, result = future.result()

    assert name == "pool-span"
    assert result == 42

def test_context_thread_pool_executor_map():
    span = Span.start_root(name="map-span")

    def worker(val: int):
        current = get_current_span()
        return current.name if current else None

    with use_span(span):
        with ContextThreadPoolExecutor(max_workers=2) as executor:
            names = list(executor.map(worker, [1, 2, 3]))

    assert names == ["map-span", "map-span", "map-span"]

def test_thread_mutation_does_not_leak():
    parent_span = Span.start_root(name="parent-span")
    pool_finished = threading.Event()

    def worker():
        # Mutate thread context
        thread_span = Span.start_root(name="thread-span")
        with use_span(thread_span):
            assert get_current_span() is thread_span
        pool_finished.set()

    with use_span(parent_span):
        with ContextThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(worker)
            pool_finished.wait()
            # Calling thread should still have parent_span
            assert get_current_span() is parent_span
