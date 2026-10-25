"""
Collector Backpressure Controller.
Enforces bounded memory and ingestion rate limits when processing queues or pipelines are full.
Explicitly rejects requests with retryable errors (HTTP 429 / 503, gRPC RESOURCE_EXHAUSTED)
and tracks rejection counters without silent data dropping.
"""

from threading import Lock

class BackpressureExceededError(Exception):
    """Raised when queue or collector admission capacity is saturated."""
    def __init__(self, message: str = "Queue capacity saturated; retry later", retry_after_seconds: int = 1):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

class BackpressureController:
    def __init__(self, max_capacity: int = 10000, default_retry_after: int = 1):
        self.max_capacity = max_capacity
        self.default_retry_after = default_retry_after
        self._current_depth = 0
        self._rejected_count = 0
        self._lock = Lock()

    @property
    def current_depth(self) -> int:
        with self._lock:
            return self._current_depth

    @property
    def rejected_count(self) -> int:
        with self._lock:
            return self._rejected_count

    def acquire(self, items: int = 1) -> None:
        with self._lock:
            if self._current_depth + items > self.max_capacity:
                self._rejected_count += 1
                raise BackpressureExceededError(
                    f"Queue saturated: depth {self._current_depth} + {items} exceeds max {self.max_capacity}",
                    retry_after_seconds=self.default_retry_after
                )
            self._current_depth += items

    def release(self, items: int = 1) -> None:
        with self._lock:
            self._current_depth = max(0, self._current_depth - items)
