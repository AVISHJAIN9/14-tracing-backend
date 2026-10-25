import pytest
from sampling.priority import PrioritySampler, PriorityLevel
from sampling.head import SamplingDecision

def test_TRC_097_priority_sampling():
    sampler = PrioritySampler(
        priority_rates={
            PriorityLevel.CRITICAL: 1.0, # 100%
            PriorityLevel.HIGH: 0.5,     # 50%
            PriorityLevel.NORMAL: 0.1,   # 10%
            PriorityLevel.LOW: 0.0,      # 0%
        },
        default_priority=PriorityLevel.NORMAL
    )

    # 1. Critical priority explicitly in attributes -> 100% sampled
    res_crit = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        attributes={"sampling.priority": "CRITICAL"}
    )
    assert res_crit.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_crit.is_sampled is True
    assert res_crit.attributes.get("priority.level") == "CRITICAL"
    assert res_crit.attributes.get("priority.rate") == 1.0

    # 2. Low priority explicitly in attributes -> 0% sampled (dropped)
    res_low = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        attributes={"priority": "low"}
    )
    assert res_low.decision == SamplingDecision.DROP
    assert res_low.is_sampled is False
    assert res_low.attributes.get("priority.level") == "LOW"

    # 3. Numeric priority support (P0=CRITICAL, P1=HIGH, P2=NORMAL, P3=LOW)
    res_p0 = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        attributes={"priority": "P0"}
    )
    assert res_p0.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_p0.attributes.get("priority.level") == "CRITICAL"

    # 4. Default fallback when no priority attribute provided
    res_default = sampler.should_sample(
        trace_id="00000000000000000000000000000001",
        attributes={}
    )
    assert res_default.attributes.get("priority.level") == "NORMAL"
    assert res_default.attributes.get("priority.rate") == 0.1
