"""
Head Sampling Implementation.
Head sampling makes a deterministic or probabilistic sampling decision at root span
creation before executing child spans or operations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

class SamplingDecision(Enum):
    DROP = "DROP"
    RECORD_ONLY = "RECORD_ONLY"
    RECORD_AND_SAMPLE = "RECORD_AND_SAMPLE"

@dataclass
class SamplingResult:
    decision: SamplingDecision
    attributes: Dict[str, Any] = field(default_factory=dict)
    trace_flags: int = 0x00

    @property
    def is_sampled(self) -> bool:
        return self.decision == SamplingDecision.RECORD_AND_SAMPLE

class HeadSampler:
    """
    Evaluates sampling policy at the head (root) of a trace.
    """
    def __init__(self, delegate: Any):
        self.delegate = delegate

    def should_sample(
        self,
        trace_id: str,
        name: str,
        parent_context: Optional[Any] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        # Delegate sampling evaluation to the underlying sampler
        attrs = dict(attributes or {})
        delegate_result = self.delegate.should_sample(
            trace_id=trace_id,
            name=name,
            attributes=attrs
        )
        decision = delegate_result.decision
        trace_flags = 0x01 if decision == SamplingDecision.RECORD_AND_SAMPLE else 0x00

        result_attrs = dict(delegate_result.attributes)
        result_attrs["sampler.type"] = "head"
        result_attrs["sampler.delegate"] = type(self.delegate).__name__

        return SamplingResult(
            decision=decision,
            attributes=result_attrs,
            trace_flags=trace_flags
        )
