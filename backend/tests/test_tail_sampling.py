import pytest
from sampling.tail import TailSampler, TailRule
from sampling.head import SamplingDecision

def test_TRC_094_tail_sampling():
    sampler = TailSampler(
        rules=[
            TailRule.error_filter(),                      # Any span in trace has ERROR
            TailRule.latency_filter(threshold_ns=500_000_000), # Total trace duration >= 500ms
            TailRule.tag_filter(key="critical", value="true")  # Any span with critical=true
        ],
        default_rate=0.0
    )

    # 1. Trace with normal spans under threshold without error -> DROPPED
    normal_spans = [
        {"span_id": "s1", "status_code": "OK", "duration_nanos": 100_000_000, "attributes": {}},
        {"span_id": "s2", "status_code": "OK", "duration_nanos": 50_000_000, "attributes": {}},
    ]
    res_normal = sampler.should_sample_trace(
        trace_id="t1",
        spans=normal_spans,
        trace_duration_ns=150_000_000
    )
    assert res_normal.decision == SamplingDecision.DROP
    assert res_normal.is_sampled is False

    # 2. Trace where second child span had ERROR -> RECORD_AND_SAMPLE
    error_spans = [
        {"span_id": "s1", "status_code": "OK", "duration_nanos": 100_000_000, "attributes": {}},
        {"span_id": "s2", "status_code": "ERROR", "duration_nanos": 50_000_000, "attributes": {}},
    ]
    res_error = sampler.should_sample_trace(
        trace_id="t2",
        spans=error_spans,
        trace_duration_ns=150_000_000
    )
    assert res_error.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_error.is_sampled is True
    assert res_error.attributes.get("tail.matched_rule") == "error_filter"

    # 3. Trace with long overall duration (600ms >= 500ms) -> RECORD_AND_SAMPLE
    slow_spans = [
        {"span_id": "s1", "status_code": "OK", "duration_nanos": 600_000_000, "attributes": {}},
    ]
    res_slow = sampler.should_sample_trace(
        trace_id="t3",
        spans=slow_spans,
        trace_duration_ns=600_000_000
    )
    assert res_slow.decision == SamplingDecision.RECORD_AND_SAMPLE
    assert res_slow.attributes.get("tail.matched_rule") == "latency_filter"
