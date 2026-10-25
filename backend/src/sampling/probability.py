"""
Probability Sampling Implementation.
Samples a configured ratio of traces (0.0 to 1.0).
Uses trace_id hashing or pseudo-randomness for deterministic or stochastic evaluation.
"""

from typing import Optional, Dict, Any
from .head import SamplingDecision, SamplingResult

class ProbabilitySampler:
    """
    Samples traces with a given probability rate in [0.0, 1.0].
    Can use trace_id hashing to ensure consistent parent/child sampling.
    """
    def __init__(self, rate: float):
        if not (0.0 <= rate <= 1.0):
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {rate}")
        self.rate = rate
        # 64-bit boundary for integer hash comparison
        self.bound = int(rate * 0xFFFFFFFFFFFFFFFF)

    def should_sample(
        self,
        trace_id: str,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        if self.rate == 0.0:
            return SamplingResult(
                decision=SamplingDecision.DROP,
                attributes={"sampler.type": "probability", "sampling.rate": 0.0},
                trace_flags=0x00
            )
        if self.rate == 1.0:
            return SamplingResult(
                decision=SamplingDecision.RECORD_AND_SAMPLE,
                attributes={"sampler.type": "probability", "sampling.rate": 1.0},
                trace_flags=0x01
            )

        try:
            val = int(trace_id, 16) % 1_000_000
            sampled = val < int(self.rate * 1_000_000)
        except (ValueError, TypeError):
            sampled = False
        decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
        trace_flags = 0x01 if sampled else 0x00

        return SamplingResult(
            decision=decision,
            attributes={"sampler.type": "probability", "sampling.rate": self.rate},
            trace_flags=trace_flags
        )
