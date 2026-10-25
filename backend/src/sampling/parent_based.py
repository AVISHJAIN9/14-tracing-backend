"""
Parent-based Sampler.
Implements the OpenTelemetry ParentBased sampler specification:
- Root spans delegate to the configured root sampler.
- Child spans with a sampled parent inherit the sampled decision.
- Child spans with an unsampled parent are dropped by default.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from .head import SamplingDecision, SamplingResult

@dataclass
class ParentContext:
    trace_id: str
    span_id: str
    is_remote: bool = False
    is_sampled: bool = False

class ParentBasedSampler:
    def __init__(
        self,
        root: Any,
        remote_parent_sampled: Optional[Any] = None,
        remote_parent_not_sampled: Optional[Any] = None,
        local_parent_sampled: Optional[Any] = None,
        local_parent_not_sampled: Optional[Any] = None,
    ):
        self.root = root
        self.remote_parent_sampled = remote_parent_sampled
        self.remote_parent_not_sampled = remote_parent_not_sampled
        self.local_parent_sampled = local_parent_sampled
        self.local_parent_not_sampled = local_parent_not_sampled

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[ParentContext] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        attrs = dict(attributes or {})

        # If no parent context exists, delegate to root sampler
        if parent_context is None:
            res = self.root.should_sample(trace_id=trace_id, name=name, attributes=attrs)
            return res

        # Remote parent
        if parent_context.is_remote:
            if parent_context.is_sampled:
                if self.remote_parent_sampled:
                    return self.remote_parent_sampled.should_sample(trace_id=trace_id, name=name, attributes=attrs)
                return SamplingResult(
                    decision=SamplingDecision.RECORD_AND_SAMPLE,
                    attributes={"sampler.type": "parent_based", "parent.is_remote": True, "parent.is_sampled": True},
                    trace_flags=0x01
                )
            else:
                if self.remote_parent_not_sampled:
                    return self.remote_parent_not_sampled.should_sample(trace_id=trace_id, name=name, attributes=attrs)
                return SamplingResult(
                    decision=SamplingDecision.DROP,
                    attributes={"sampler.type": "parent_based", "parent.is_remote": True, "parent.is_sampled": False},
                    trace_flags=0x00
                )

        # Local parent
        if parent_context.is_sampled:
            if self.local_parent_sampled:
                return self.local_parent_sampled.should_sample(trace_id=trace_id, name=name, attributes=attrs)
            return SamplingResult(
                decision=SamplingDecision.RECORD_AND_SAMPLE,
                attributes={"sampler.type": "parent_based", "parent.is_remote": False, "parent.is_sampled": True},
                trace_flags=0x01
            )
        else:
            if self.local_parent_not_sampled:
                return self.local_parent_not_sampled.should_sample(trace_id=trace_id, name=name, attributes=attrs)
            return SamplingResult(
                decision=SamplingDecision.DROP,
                attributes={"sampler.type": "parent_based", "parent.is_remote": False, "parent.is_sampled": False},
                trace_flags=0x00
            )
