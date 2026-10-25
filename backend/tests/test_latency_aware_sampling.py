import pytest
from sampling.latency_sampler import LatencyAwareSampler
from sampling.probability import ProbabilitySampler
from sampling.head import SamplingDecision

def test_TRC_093_latency_aware_sampling():
    # Base sampler drops everything (rate=0.0)
    base_sampler = ProbabilitySampler(rate=0.0)
    # Threshold: 200 milliseconds (200_000_000 ns)
    sampler = LatencyAwareSampler(threshold_nanos=200_000_000, fallback_sampler=base_sampler)

    # 1. Fast span (50ms) -> falls back to base_sampler -> DROPPED
    res_fast = sampler.evaluate_latency(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        duration_nanos=50_000_000
    )
    assert res_fast.decision == SamplingDecision.DROP
    assert res_fast.is_sampled is False

    # 2. Slow span (350ms > 200ms threshold) -> RECORD_AND_SAMPLE (100% kept)
    res_slow = sampler.evaluate_latency(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        duration_nanos=350_000_000
    )
    assert res_slow.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_slow.is_sampled is True
    assert res_slow.attributes.get("sampling.reason") == "latency_threshold_exceeded"
    assert res_slow.attributes.get("latency.duration_nanos") == 350_000_000

    # 3. Exactly at threshold (200ms) -> sampled
    res_exact = sampler.evaluate_latency(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        duration_nanos=200_000_000
    )
    assert res_exact.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_exact.is_sampled is True
