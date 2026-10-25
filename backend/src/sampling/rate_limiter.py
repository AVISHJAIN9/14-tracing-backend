"""
Rate-based Sampling Implementation.
Controls sampling rate using a Token Bucket algorithm allowing configurable
steady-state rates (traces per second) and burst allowances.
"""

import time
import threading
from typing import Optional, Dict, Any, Callable
from .head import SamplingDecision, SamplingResult

class RateBasedSampler:
    """
    Rate-based sampler using Token Bucket.
    Enforces a strict upper bound of sampled traces per second.
    """
    def __init__(
        self,
        max_per_second: float,
        burst_size: Optional[int] = None,
        clock_fn: Optional[Callable[[], float]] = None
    ):
        if max_per_second <= 0:
            raise ValueError(f"max_per_second must be positive, got {max_per_second}")

        self.max_per_second = float(max_per_second)
        self.burst_size = burst_size if burst_size is not None else int(max_per_second)
        self.clock_fn = clock_fn or time.time
        self.lock = threading.Lock()

        # Token bucket state
        self.tokens = float(self.burst_size)
        self.last_update = self.clock_fn()

    def should_sample(
        self,
        trace_id: str,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        with self.lock:
            now = self.clock_fn()
            elapsed = max(0.0, now - self.last_update)
            self.last_update = now

            # Replenish tokens based on elapsed time
            self.tokens = min(float(self.burst_size), self.tokens + elapsed * self.max_per_second)

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                decision = SamplingDecision.RECORD_AND_SAMPLE
                trace_flags = 0x01
            else:
                decision = SamplingDecision.DROP
                trace_flags = 0x00

        return SamplingResult(
            decision=decision,
            attributes={
                "sampler.type": "rate_based",
                "max_per_second": self.max_per_second,
                "burst_size": self.burst_size
            },
            trace_flags=trace_flags
        )
