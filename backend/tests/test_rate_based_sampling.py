import pytest
from sampling.rate_limiter import RateBasedSampler
from sampling.head import SamplingDecision

class FakeClock:
    def __init__(self, start_time: float = 1000.0):
        self.current_time = start_time

    def time(self) -> float:
        return self.current_time

    def advance(self, seconds: float):
        self.current_time += seconds

def test_TRC_086_rate_based_sampling():
    clock = FakeClock()
    # 5 samples per second, burst size of 5
    sampler = RateBasedSampler(max_per_second=5.0, burst_size=5, clock_fn=clock.time)

    # First 5 requests within the burst capacity should all be sampled
    for i in range(5):
        res = sampler.should_sample(f"trace-{i}", "op")
        assert res.decision == SamplingDecision.RECORD_AND_SAMPLE
        assert res.is_sampled is True

    # 6th request immediately at t=1000 has no tokens left -> DROPPED
    res6 = sampler.should_sample("trace-6", "op")
    assert res6.decision == SamplingDecision.DROP
    assert res6.is_sampled is False

    # Advance clock by 0.5 seconds -> 2.5 tokens added (floor 2 tokens)
    clock.advance(0.5)
    assert sampler.should_sample("trace-7", "op").is_sampled is True
    assert sampler.should_sample("trace-8", "op").is_sampled is True
    assert sampler.should_sample("trace-9", "op").is_sampled is False

    # Advance clock by 2 seconds -> capacity fills back up to burst_size (5)
    clock.advance(2.0)
    for i in range(5):
        assert sampler.should_sample(f"trace-burst-{i}", "op").is_sampled is True
    assert sampler.should_sample("trace-overflow", "op").is_sampled is False
