import pytest
from sampling.policies import SamplingPolicyEngine, SamplingRule
from sampling.head import SamplingDecision

def test_TRC_089_sampling_policies():
    engine = SamplingPolicyEngine(
        rules=[
            # Critical payment route always sampled (100%)
            SamplingRule(
                name="payments_rule",
                service_pattern="payment-.*",
                route_pattern="/checkout/.*",
                sample_rate=1.0
            ),
            # Health check routes dropped (0%)
            SamplingRule(
                name="health_check_rule",
                route_pattern="/healthz|/readyz",
                sample_rate=0.0
            ),
            # Background jobs at 10%
            SamplingRule(
                name="batch_jobs",
                service_pattern="worker-.*",
                sample_rate=0.1
            ),
        ],
        default_rate=0.2
    )

    # 1. Matches payment rule -> 100% sampled
    res_pay = engine.evaluate(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        service_name="payment-gateway",
        operation_name="/checkout/submit"
    )
    assert res_pay.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_pay.is_sampled is True
    assert res_pay.attributes.get("sampling.rule") == "payments_rule"

    # 2. Matches health check rule -> DROPPED
    res_health = engine.evaluate(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        service_name="frontend-api",
        operation_name="/healthz"
    )
    assert res_health.decision == SamplingDecision.DROP
    assert res_health.is_sampled is False
    assert res_health.attributes.get("sampling.rule") == "health_check_rule"

    # 3. Unmatched service/route falls back to default_rate
    res_default = engine.evaluate(
        trace_id="00000000000000000000000000000001",
        service_name="other-svc",
        operation_name="/api/v1/users"
    )
    assert res_default.attributes.get("sampling.rule") == "default"
