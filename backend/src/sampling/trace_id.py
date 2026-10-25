"""
Trace-ID Ratio Sampler.
Samples traces strictly based on deterministic evaluation of the 128-bit trace ID.
Guarantees that disparate services receiving the same trace ID independently compute
the exact same sampling decision.
"""

from typing import Optional, Dict, Any
from .head import SamplingDecision, SamplingResult

class TraceIdRatioSampler:
    """
    Deterministic ratio sampler based on trace_id.
    """
    def __init__(self, ratio: float):
        if not (0.0 <= ratio <= 1.0):
            raise ValueError(f"Trace ID sampling ratio must be in [0.0, 1.0], got {ratio}")
        self.ratio = ratio
        self.bound = int(ratio * 1_000_000)

    def should_sample(
        self,
        trace_id: str,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        try:
            val = int(trace_id, 16) % 1_000_000
            sampled = val < self.bound
        except (ValueError, TypeError):
            sampled = False

        decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
        trace_flags = 0x01 if sampled else 0x00

        return SamplingResult(
            decision=decision,
            attributes={
                "sampler.type": "trace_id_ratio",
                "sampler.ratio": self.ratio,
                "trace_id": trace_id
            },
            trace_flags=trace_flags
        )
