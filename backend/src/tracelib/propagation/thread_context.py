"""
tracelib.propagation.thread_context — Thread Context Propagation.
Propagates active Span and context across OS thread pools and worker threads.
"""

import functools
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from typing import Any, Callable, Iterable, Optional

def wrap_callable_with_context(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Wrap a callable so that it executes within a copy of the current contextvars
    active at the time of wrapping.
    """
    ctx = copy_context()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return ctx.run(func, *args, **kwargs)

    return wrapper

class ContextThreadPoolExecutor(ThreadPoolExecutor):
    """
    ThreadPoolExecutor that captures the active context at task submission time
    and executes submitted tasks inside that context.
    """

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        ctx = copy_context()

        def run_in_context(*a, **kw):
            return ctx.run(fn, *a, **kw)

        return super().submit(run_in_context, *args, **kwargs)

    def map(
        self,
        func: Callable[..., Any],
        *iterables: Iterable[Any],
        timeout: Optional[float] = None,
        chunksize: int = 1,
    ):
        ctx = copy_context()

        def run_in_context(*a, **kw):
            return ctx.run(func, *a, **kw)

        return super().map(run_in_context, *iterables, timeout=timeout, chunksize=chunksize)
