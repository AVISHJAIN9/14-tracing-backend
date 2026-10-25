import pytest
from sampling.service_sampler import PerServiceSampler
from sampling.head import SamplingDecision

def test_TRC_090_per_service_sampling():
    sampler = PerServiceSampler(
        service_rates={
            "checkout-svc": 1.0,      # 100%
            "metrics-daemon": 0.0,    # 0%
            "user-svc": 0.5           # 50%
        },
        default_rate=0.1              # 10%
    )

    # 1. checkout-svc always sampled
    for i in range(20):
        res = sampler.should_sample(trace_id=f"{i:032x}", service_name="checkout-svc")
        assert res.decision == SamplingDecision.RECORD_AND_SAMPLE
        assert res.is_sampled is True
        assert res.attributes.get("service.name") == "checkout-svc"
        assert res.attributes.get("service.sample_rate") == 1.0

    # 2. metrics-daemon always dropped
    for i in range(20):
        res = sampler.should_sample(trace_id=f"{i:032x}", service_name="metrics-daemon")
        assert res.decision == SamplingDecision.DROP
        assert res.is_sampled is False
        assert res.attributes.get("service.sample_rate") == 0.0

    # 3. Dynamic service rate update
    sampler.set_service_rate("metrics-daemon", 1.0)
    res_updated = sampler.should_sample(trace_id="1234567890abcdef1234567890abcdef", service_name="metrics-daemon")
    assert res_updated.decision == SamplingDecision.RECORD_AND_SAMPLE

    # 4. Fallback to default_rate
    res_default = sampler.should_sample(trace_id="00000000000000000000000000000001", service_name="unregistered-svc")
    assert res_default.attributes.get("service.sample_rate") == 0.1
