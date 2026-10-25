import pytest
from sampling.tail_buffer import TailSamplingBuffer
from sampling.tail import TailSampler, TailRule

class FakeClock:
    def __init__(self, start_time: float = 100.0):
        self.cur = start_time
    def now(self) -> float:
        return self.cur
    def advance(self, s: float):
        self.cur += s

def test_TRC_095_tail_sampling_buffer():
    clock = FakeClock()
    sampler = TailSampler(rules=[TailRule.error_filter()], default_rate=0.0)

    # Max 3 traces buffer, 5.0 seconds decision window
    buf = TailSamplingBuffer(
        max_traces=3,
        decision_window_seconds=5.0,
        sampler=sampler,
        clock_fn=clock.now
    )

    # Ingest spans for trace t1 (normal)
    buf.add_span(trace_id="t1", span_id="s1", status_code="OK", start_time_ns=1000, duration_ns=100)
    assert buf.trace_count == 1

    # Ingest span for trace t2 (has error)
    buf.add_span(trace_id="t2", span_id="s2", status_code="ERROR", start_time_ns=2000, duration_ns=100)
    assert buf.trace_count == 2

    # Advance clock by 2 seconds (not yet expired window) -> flush returns nothing
    clock.advance(2.0)
    ready = buf.flush_ready_traces()
    assert len(ready) == 0

    # Advance clock past 5.0s decision window
    clock.advance(4.0)
    # Ready traces should now be evaluated
    decided = buf.flush_ready_traces()
    # t1 had no errors -> dropped (not returned)
    # t2 had an error -> sampled (returned)
    sampled_trace_ids = [t.trace_id for t in decided]
    assert "t2" in sampled_trace_ids
    assert "t1" not in sampled_trace_ids
    assert buf.trace_count == 0

    # Capacity overflow test: buffer bounded to max_traces=3
    buf.add_span("ta", "sa", "OK", 1000, 100)
    buf.add_span("tb", "sb", "OK", 1000, 100)
    buf.add_span("tc", "sc", "OK", 1000, 100)
    # 4th trace exceeds max_traces
    overflow_accepted = buf.add_span("td", "sd", "OK", 1000, 100)
    assert overflow_accepted is False  # Rejected / bounded
    assert buf.drop_count >= 1
