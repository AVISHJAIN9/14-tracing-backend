"""
Ingestion Retry Engine.
Exponential backoff retry handler for transient database errors, deadlocks,
and socket resets during span batch ingestion.
"""

import asyncio
from typing import Any, Callable, Coroutine, TypeVar
from sqlalchemy.exc import DBAPIError, OperationalError

T = TypeVar("T")

class IngestionRetryExhaustedError(Exception):
    """Raised when maximum retry attempts have been exhausted."""
    pass

class RetryableIngester:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.05,
        max_delay: float = 2.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def is_transient_error(self, exc: Exception) -> bool:
        if isinstance(exc, (OperationalError, ConnectionResetError, TimeoutError)):
            return True
        if isinstance(exc, DBAPIError) and exc.connection_invalidated:
            return True
        msg = str(exc).lower()
        transient_keywords = ("connection", "deadlock", "timeout", "reset", "closed", "unavailable")
        return any(k in msg for k in transient_keywords)

    async def execute_with_retry(
        self,
        operation: Callable[[], Coroutine[Any, Any, T]],
        max_retries: int | None = None
    ) -> T:
        limit = max_retries if max_retries is not None else self.max_retries
        attempt = 0
        last_error: Exception | None = None

        while attempt < limit:
            try:
                return await operation()
            except Exception as e:
                attempt += 1
                last_error = e
                if not self.is_transient_error(e) or attempt >= limit:
                    break

                delay = min(self.max_delay, self.base_delay * (self.backoff_factor ** (attempt - 1)))
                await asyncio.sleep(delay)  # Exponential backoff delay before retrying transient failure

        raise IngestionRetryExhaustedError(
            f"Max retries ({limit}) exhausted. Last error: {str(last_error)}"
        ) from last_error
