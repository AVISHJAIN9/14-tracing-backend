"""
Error-aware Sampling Implementation.
Guarantees that error spans/traces (status ERROR, exception attributes, HTTP 5xx)
are retained at high priority (default 100%), overriding head drops.
"""

from typing import Optional, Dict, Any
from .head import SamplingDecision, SamplingResult

class ErrorAwareSampler:
    def __init__(self, fallback_sampler: Any, error_sample_rate: float = 1.0):
        self.fallback_sampler = fallback_sampler
        self.error_sample_rate = error_sample_rate

    def _is_error(self, status_code: Optional[str], attributes: Optional[Dict[str, Any]]) -> bool:
        if status_code == "ERROR":
            return True

        attrs = attributes or {}
        # Check HTTP status >= 500
        http_status = attrs.get("http.status_code") or attrs.get("http.response.status_code")
        if http_status is not None:
            try:
                if int(http_status) >= 500:
                    return True
            except (ValueError, TypeError):
                pass

        # Check for exception attributes
        if "exception.type" in attrs or "exception.message" in attrs or "error" in attrs:
            return True

        return False

    def evaluate_span(
        self,
        trace_id: str,
        status_code: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        name: str = "span"
    ) -> SamplingResult:
        attrs = dict(attributes or {})
        if self._is_error(status_code, attrs):
            try:
                val = int(trace_id, 16) % 1_000_000
                sampled = val < int(self.error_sample_rate * 1_000_000)
            except (ValueError, TypeError):
                sampled = True

            decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
            trace_flags = 0x01 if sampled else 0x00
            return SamplingResult(
                decision=decision,
                attributes={
                    "sampler.type": "error_aware",
                    "sampling.reason": "error_detected",
                    "error.sample_rate": self.error_sample_rate
                },
                trace_flags=trace_flags
            )

        # Delegate non-error span to fallback sampler
        return self.fallback_sampler.should_sample(
            trace_id=trace_id,
            name=name,
            attributes=attrs
        )
