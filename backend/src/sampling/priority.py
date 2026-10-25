"""
Priority Sampling Implementation.
Classifies traces by priority classes (CRITICAL / P0, HIGH / P1, NORMAL / P2, LOW / P3)
derived from span attributes or tracestate, applying priority-specific sampling rates.
"""

from enum import Enum
from typing import Dict, Optional, Any
from .head import SamplingDecision, SamplingResult

class PriorityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"

_PRIORITY_ALIASES = {
    "critical": PriorityLevel.CRITICAL,
    "p0": PriorityLevel.CRITICAL,
    "0": PriorityLevel.CRITICAL,
    "high": PriorityLevel.HIGH,
    "p1": PriorityLevel.HIGH,
    "1": PriorityLevel.HIGH,
    "normal": PriorityLevel.NORMAL,
    "p2": PriorityLevel.NORMAL,
    "2": PriorityLevel.NORMAL,
    "low": PriorityLevel.LOW,
    "p3": PriorityLevel.LOW,
    "3": PriorityLevel.LOW,
}

class PrioritySampler:
    def __init__(
        self,
        priority_rates: Optional[Dict[PriorityLevel, float]] = None,
        default_priority: PriorityLevel = PriorityLevel.NORMAL
    ):
        self.priority_rates = priority_rates or {
            PriorityLevel.CRITICAL: 1.0,
            PriorityLevel.HIGH: 0.5,
            PriorityLevel.NORMAL: 0.1,
            PriorityLevel.LOW: 0.01,
        }
        self.default_priority = default_priority

    def _extract_priority(self, attributes: Optional[Dict[str, Any]]) -> PriorityLevel:
        attrs = attributes or {}
        val = attrs.get("sampling.priority") or attrs.get("priority")
        if val is not None:
            normalized = str(val).strip().lower()
            if normalized in _PRIORITY_ALIASES:
                return _PRIORITY_ALIASES[normalized]
        return self.default_priority

    def should_sample(
        self,
        trace_id: str,
        name: str = "span",
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        priority = self._extract_priority(attributes)
        rate = self.priority_rates.get(priority, 0.1)

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
                "sampler.type": "priority",
                "priority.level": priority.value,
                "priority.rate": rate
            },
            trace_flags=trace_flags
        )
