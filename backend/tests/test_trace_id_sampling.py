import pytest
from sampling.trace_id import TraceIdRatioSampler
from sampling.head import SamplingDecision

def test_TRC_088_trace_id_sampling():
    # Ratio 0.25 (25%)
    sampler = TraceIdRatioSampler(ratio=0.25)

    # Identical trace ID must produce identical sampling decision every time
    t_fixed = "1234567890abcdef1234567890abcdef"
    first_decision = sampler.should_sample(t_fixed, "op1")
    for _ in range(20):
        subsequent = sampler.should_sample(t_fixed, "different_op")
        assert subsequent.decision == first_decision.decision
        assert subsequent.trace_flags == first_decision.trace_flags

    # Multi-service simulation: Service A and Service B evaluating the same trace ID independently
    sampler_svc_a = TraceIdRatioSampler(ratio=0.33)
    sampler_svc_b = TraceIdRatioSampler(ratio=0.33)

    for i in range(100):
        tid = f"{i:032x}"
        decision_a = sampler_svc_a.should_sample(tid, "svc_a_op")
        decision_b = sampler_svc_b.should_sample(tid, "svc_b_op")
        assert decision_a.decision == decision_b.decision
        assert decision_a.trace_flags == decision_b.trace_flags

    # Invalid ratio raises ValueError
    with pytest.raises(ValueError):
        TraceIdRatioSampler(ratio=-0.5)
    with pytest.raises(ValueError):
        TraceIdRatioSampler(ratio=1.5)
