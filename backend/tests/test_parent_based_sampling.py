import pytest
from sampling.parent_based import ParentBasedSampler, ParentContext
from sampling.head import SamplingDecision
from sampling.probability import ProbabilitySampler

def test_TRC_087_parent_based_sampling():
    root_sampler = ProbabilitySampler(rate=0.0) # root drops by default
    sampler = ParentBasedSampler(root=root_sampler)

    # 1. No parent context -> delegates to root sampler (rate=0.0 -> DROP)
    res_root = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        name="root_op",
        parent_context=None
    )
    assert res_root.decision == SamplingDecision.DROP
    assert res_root.is_sampled is False

    # 2. Remote parent sampled -> inherits sampled decision
    parent_remote_sampled = ParentContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7", is_remote=True, is_sampled=True)
    res_remote_sampled = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        name="child_op",
        parent_context=parent_remote_sampled
    )
    assert res_remote_sampled.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_remote_sampled.is_sampled is True

    # 3. Remote parent NOT sampled -> drops
    parent_remote_unsampled = ParentContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7", is_remote=True, is_sampled=False)
    res_remote_unsampled = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        name="child_op",
        parent_context=parent_remote_unsampled
    )
    assert res_remote_unsampled.decision == SamplingDecision.DROP
    assert res_remote_unsampled.is_sampled is False

    # 4. Local parent sampled -> inherits sampled decision
    parent_local_sampled = ParentContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7", is_remote=False, is_sampled=True)
    res_local = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        name="local_child",
        parent_context=parent_local_sampled
    )
    assert res_local.decision == SamplingDecision.RECORD_AND_SAMPLE
