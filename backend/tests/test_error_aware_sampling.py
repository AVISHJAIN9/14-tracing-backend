import pytest
from sampling.error_aware import ErrorAwareSampler
from sampling.probability import ProbabilitySampler
from sampling.head import SamplingDecision

def test_TRC_092_error_aware_sampling():
    # Base sampler drops everything (rate=0.0)
    base_sampler = ProbabilitySampler(rate=0.0)
    sampler = ErrorAwareSampler(fallback_sampler=base_sampler, error_sample_rate=1.0)

    # 1. Non-error span without error attributes -> evaluated by fallback (rate=0.0 -> DROP)
    res_normal = sampler.evaluate_span(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        status_code="OK",
        attributes={"http.status_code": 200}
    )
    assert res_normal.decision == SamplingDecision.DROP
    assert res_normal.is_sampled is False

    # 2. Span with status_code == "ERROR" -> Guaranteed 100% sampling
    res_error_status = sampler.evaluate_span(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        status_code="ERROR",
        attributes={"http.status_code": 200}
    )
    assert res_error_status.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_error_status.is_sampled is True
    assert res_error_status.attributes.get("sampling.reason") == "error_detected"

    # 3. Span with HTTP 500 status code attribute -> Treated as error and sampled
    res_http_500 = sampler.evaluate_span(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        status_code="UNSET",
        attributes={"http.status_code": 500}
    )
    assert res_http_500.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_http_500.is_sampled is True

    # 4. Span with exception event or exception.type attribute
    res_exc = sampler.evaluate_span(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        status_code="UNSET",
        attributes={"exception.type": "DatabaseTimeoutError"}
    )
    assert res_exc.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_exc.is_sampled is True
