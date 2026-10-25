"""
Sampling Policies Engine.
Evaluates sequential rules matching service names, routes/operation names, and attributes
to apply specific sampling rates or decisions.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from .head import SamplingDecision, SamplingResult

@dataclass
class SamplingRule:
    name: str
    service_pattern: Optional[str] = None
    route_pattern: Optional[str] = None
    sample_rate: float = 1.0
    attributes_match: Optional[Dict[str, str]] = None

    def matches(self, service_name: str, operation_name: str, attributes: Optional[Dict[str, Any]] = None) -> bool:
        if self.service_pattern and not re.fullmatch(self.service_pattern, service_name):
            return False
        if self.route_pattern and not re.fullmatch(self.route_pattern, operation_name):
            return False
        if self.attributes_match:
            attrs = attributes or {}
            for k, v in self.attributes_match.items():
                if str(attrs.get(k)) != str(v):
                    return False
        return True

class SamplingPolicyEngine:
    def __init__(self, rules: Optional[List[SamplingRule]] = None, default_rate: float = 0.1):
        self.rules = rules or []
        self.default_rate = default_rate

    def evaluate(
        self,
        trace_id: str,
        service_name: str,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        attrs = dict(attributes or {})

        # Evaluate rules in sequential order
        for rule in self.rules:
            if rule.matches(service_name, operation_name, attrs):
                try:
                    val = int(trace_id, 16) % 1_000_000
                    sampled = val < int(rule.sample_rate * 1_000_000)
                except (ValueError, TypeError):
                    sampled = False

                decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
                trace_flags = 0x01 if sampled else 0x00
                return SamplingResult(
                    decision=decision,
                    attributes={
                        "sampler.type": "policy_rule",
                        "sampling.rule": rule.name,
                        "sampling.rate": rule.sample_rate
                    },
                    trace_flags=trace_flags
                )

        # Default fallback
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
                "sampler.type": "policy_default",
                "sampling.rule": "default",
                "sampling.rate": self.default_rate
            },
            trace_flags=trace_flags
        )
