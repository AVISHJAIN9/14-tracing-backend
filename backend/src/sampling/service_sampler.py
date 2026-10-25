"""
Per-Service Sampling Configuration.
Allows configuring and updating dedicated sampling ratios per service name.
"""

from typing import Dict, Optional, Any
from .head import SamplingDecision, SamplingResult

class PerServiceSampler:
    def __init__(self, service_rates: Optional[Dict[str, float]] = None, default_rate: float = 0.1):
        self.service_rates: Dict[str, float] = dict(service_rates or {})
        self.default_rate = default_rate

    def set_service_rate(self, service_name: str, rate: float) -> None:
        if not (0.0 <= rate <= 1.0):
            raise ValueError(f"Rate must be between 0.0 and 1.0, got {rate}")
        self.service_rates[service_name] = rate

    def should_sample(
        self,
        trace_id: str,
        service_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        rate = self.service_rates.get(service_name, self.default_rate)

        try:
            val = int(trace_id, 16) % 1_000_000
            sampled = val < int(rate * 1_000_000)
        except (ValueError, TypeError):
            sampled = False

        decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
        trace_flags = 0x01 if sampled else 0x00

        return SamplingResult(
            decision=decision,
            attributes={
                "sampler.type": "per_service",
                "service.name": service_name,
                "service.sample_rate": rate
            },
            trace_flags=trace_flags
        )
