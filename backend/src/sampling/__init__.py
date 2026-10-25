"""
Sampling and Tail Analysis package for distributed tracing backend.
"""

from .head import HeadSampler, SamplingDecision, SamplingResult
from .probability import ProbabilitySampler
from .rate_limiter import RateBasedSampler
from .parent_based import ParentBasedSampler, ParentContext
from .trace_id import TraceIdRatioSampler
from .policies import SamplingPolicyEngine, SamplingRule
from .service_sampler import PerServiceSampler
from .route_sampler import PerRouteSampler
from .error_aware import ErrorAwareSampler
from .latency_sampler import LatencyAwareSampler
from .tail import TailSampler, TailRule
from .tail_buffer import TailSamplingBuffer, BufferedTrace, BufferedSpan
from .tail_window import TailDecisionWindow, TraceWindowState
from .priority import PrioritySampler, PriorityLevel

__all__ = [
    "HeadSampler",
    "SamplingDecision",
    "SamplingResult",
    "ProbabilitySampler",
    "RateBasedSampler",
    "ParentBasedSampler",
    "ParentContext",
    "TraceIdRatioSampler",
    "SamplingPolicyEngine",
    "SamplingRule",
    "PerServiceSampler",
    "PerRouteSampler",
    "ErrorAwareSampler",
    "LatencyAwareSampler",
    "TailSampler",
    "TailRule",
    "TailSamplingBuffer",
    "BufferedTrace",
    "BufferedSpan",
    "TailDecisionWindow",
    "TraceWindowState",
    "PrioritySampler",
    "PriorityLevel",
]
