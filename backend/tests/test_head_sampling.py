import pytest
from sampling.head import HeadSampler, SamplingDecision
from sampling.probability import ProbabilitySampler

def test_TRC_084_head_sampling():
    # HeadSampler evaluates at root span creation before span execution
    sampler_always_on = HeadSampler(delegate=ProbabilitySampler(rate=1.0))
    sampler_always_off = HeadSampler(delegate=ProbabilitySampler(rate=0.0))

    # Root span with no parent
    res_on = sampler_always_on.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        name="root_operation",
        parent_context=None,
        attributes={"http.route": "/checkout"}
    )
    assert res_on.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_on.is_sampled is True
    assert res_on.trace_flags == 0x01
    assert "sampler.type" in res_on.attributes

    # Sampler off
    res_off = sampler_always_off.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        name="root_operation",
        parent_context=None,
        attributes={"http.route": "/checkout"}
    )
    assert res_off.decision == SamplingDecision.DROP
    assert res_off.is_sampled is False
    assert res_off.trace_flags == 0x00
