"""
tracelib.propagation.async_context — Asyncio ContextVars Propagation.
Maintains the active Span and context across async tasks and nested scopes.
"""

from contextvars import ContextVar, Token
from typing import Optional
from tracelib.core.span import Span

_CURRENT_SPAN: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)

def get_current_span() -> Optional[Span]:
    """Return the active Span in the current async context, or None."""
    return _CURRENT_SPAN.get()

def attach_span(span: Optional[Span]) -> Token:
    """
    Set the active Span in the current async context.
    Returns a Token that can be used to restore the previous context.
    """
    return _CURRENT_SPAN.set(span)

def detach_span(token: Token) -> None:
    """Reset the context to the state prior to the attach call."""
    _CURRENT_SPAN.reset(token)

class _SpanContextManager:
    """Dual sync and async context manager activating a Span in contextvars."""

    def __init__(self, span: Optional[Span]):
        self._span = span
        self._token: Optional[Token] = None

    def __enter__(self) -> Optional[Span]:
        self._token = attach_span(self._span)
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._token is not None:
            detach_span(self._token)
            self._token = None

    async def __aenter__(self) -> Optional[Span]:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

def use_span(span: Optional[Span]) -> _SpanContextManager:
    """
    Activate a Span as the current active span within a `with` or `async with` block.
    Restores the previous context automatically on exit.
    """
    return _SpanContextManager(span)
