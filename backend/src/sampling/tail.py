"""
Tail Sampling Engine.
Evaluates complete traces (all collected spans in a trace window) against multi-attribute
policies (error detection, latency thresholds, tag matches) to make holistic sampling decisions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from .head import SamplingDecision, SamplingResult

@dataclass
class TailRule:
    name: str
    evaluator: Callable[[List[Dict[str, Any]], int], bool]

    @classmethod
    def error_filter(cls) -> "TailRule":
        def check(spans: List[Dict[str, Any]], trace_duration_ns: int) -> bool:
            for s in spans:
                if s.get("status_code") == "ERROR":
                    return True
                attrs = s.get("attributes") or {}
                if attrs.get("http.status_code") and int(attrs.get("http.status_code", 0)) >= 500:
                    return True
                if "exception.type" in attrs or "error" in attrs:
                    return True
            return False
        return cls(name="error_filter", evaluator=check)

    @classmethod
    def latency_filter(cls, threshold_ns: int) -> "TailRule":
        def check(spans: List[Dict[str, Any]], trace_duration_ns: int) -> bool:
            return trace_duration_ns >= threshold_ns
        return cls(name="latency_filter", evaluator=check)

    @classmethod
    def tag_filter(cls, key: str, value: Any) -> "TailRule":
        def check(spans: List[Dict[str, Any]], trace_duration_ns: int) -> bool:
            for s in spans:
                attrs = s.get("attributes") or {}
                if str(attrs.get(key)) == str(value):
                    return True
            return False
        return cls(name=f"tag_filter_{key}", evaluator=check)

class TailSampler:
    def __init__(self, rules: Optional[List[TailRule]] = None, default_rate: float = 0.0):
        self.rules = rules or []
        self.default_rate = default_rate

    def should_sample_trace(
        self,
        trace_id: str,
        spans: List[Dict[str, Any]],
        trace_duration_ns: int
    ) -> SamplingResult:
        # Evaluate tail rules against the trace
        for rule in self.rules:
            if rule.evaluator(spans, trace_duration_ns):
                return SamplingResult(
                    decision=SamplingDecision.RECORD_AND_SAMPLE,
                    attributes={
                        "sampler.type": "tail",
                        "tail.matched_rule": rule.name,
                        "tail.span_count": len(spans),
                        "tail.trace_duration_ns": trace_duration_ns
                    },
                    trace_flags=0x01
                )

        # Fallback default probability
        try:
            val = int(trace_id, 16) % 1_000_000
            sampled = val < int(self.default_rate * 1_000_000)
        except (ValueError, TypeError):
            sampled = False

        decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
        trace_flags = 0x01 if sampled else 0x00

        return SamplingResult(
            decision=decision,
            attributes={
                "sampler.type": "tail_default",
                "tail.sample_rate": self.default_rate
            },
            trace_flags=trace_flags
        )
