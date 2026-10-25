"""
Latency-aware Sampling Implementation.
Retains traces whose duration meets or exceeds a configured latency threshold.
"""

from typing import Optional, Dict, Any
from .head import SamplingDecision, SamplingResult

class LatencyAwareSampler:
    def __init__(
        self,
        threshold_nanos: int,
        fallback_sampler: Any,
        sample_rate_above_threshold: float = 1.0
    ):
        if threshold_nanos < 0:
            raise ValueError(f"threshold_nanos must be non-negative, got {threshold_nanos}")
        self.threshold_nanos = threshold_nanos
        self.fallback_sampler = fallback_sampler
        self.sample_rate_above_threshold = sample_rate_above_threshold

    def evaluate_latency(
        self,
        trace_id: str,
        duration_nanos: int,
        attributes: Optional[Dict[str, Any]] = None,
        name: str = "span"
    ) -> SamplingResult:
        attrs = dict(attributes or {})

        # If latency meets or exceeds threshold -> Sample
        if duration_nanos >= self.threshold_nanos:
            try:
                val = int(trace_id, 16) % 1_000_000
                sampled = val < int(self.sample_rate_above_threshold * 1_000_000)
            except (ValueError, TypeError):
                sampled = True

            decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
            trace_flags = 0x01 if sampled else 0x00

            return SamplingResult(
                decision=decision,
                attributes={
                    "sampler.type": "latency_aware",
                    "sampling.reason": "latency_threshold_exceeded",
                    "latency.duration_nanos": duration_nanos,
                    "latency.threshold_nanos": self.threshold_nanos
                },
                trace_flags=trace_flags
            )

        # Delegate below-threshold spans to fallback sampler
        return self.fallback_sampler.should_sample(
            trace_id=trace_id,
            name=name,
            attributes=attrs
        )
