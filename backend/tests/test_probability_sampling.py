import pytest
import uuid
from sampling.probability import ProbabilitySampler
from sampling.head import SamplingDecision

def test_TRC_085_probability_sampling():
    # Boundary tests
    sampler_0 = ProbabilitySampler(rate=0.0)
    sampler_1 = ProbabilitySampler(rate=1.0)

    for _ in range(50):
        tid = uuid.uuid4().hex
        assert sampler_0.should_sample(tid, "op").decision == SamplingDecision.DROP
        assert sampler_1.should_sample(tid, "op").decision == SamplingDecision.RECORD_AND_SAMPLE

    # Invalid rate raises ValueError
    with pytest.raises(ValueError):
        ProbabilitySampler(rate=-0.1)
    with pytest.raises(ValueError):
        ProbabilitySampler(rate=1.5)

    # Statistical test: 50% sampling over 2,000 samples
    sampler_half = ProbabilitySampler(rate=0.5)
    sampled_count = 0
    total = 2000
    for _ in range(total):
        tid = uuid.uuid4().hex
        if sampler_half.should_sample(tid, "op").is_sampled:
            sampled_count += 1

    ratio = sampled_count / total
    # 0.5 +/- 0.06 is > 4 standard deviations for N=2000
    assert 0.44 <= ratio <= 0.56
