import pytest
from sampling.route_sampler import PerRouteSampler
from sampling.head import SamplingDecision

def test_TRC_091_per_route_sampling():
    sampler = PerRouteSampler(
        route_rates={
            "/api/v1/pay": 1.0,           # 100%
            "/healthz": 0.0,              # 0%
            "/users/{id}/profile": 0.5,   # Parameterized route 50%
        },
        default_rate=0.05
    )

    # 1. Exact route match /api/v1/pay
    res_pay = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        route="/api/v1/pay"
    )
    assert res_pay.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_pay.is_sampled is True
    assert res_pay.attributes.get("http.route") == "/api/v1/pay"

    # 2. Exact match /healthz -> dropped
    res_health = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        route="/healthz"
    )
    assert res_health.decision == SamplingDecision.DROP
    assert res_health.is_sampled is False

    # 3. Parameterized pattern match /users/{id}/profile
    res_profile = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        route="/users/12345/profile"
    )
    assert res_profile.attributes.get("route.matched_template") == "/users/{id}/profile"

    # 4. Unmatched route uses default_rate (0.05)
    res_unmatched = sampler.should_sample(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        route="/static/favicon.ico"
    )
    assert res_unmatched.attributes.get("route.sample_rate") == 0.05
