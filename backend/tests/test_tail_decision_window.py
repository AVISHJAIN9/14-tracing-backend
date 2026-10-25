import pytest
from sampling.tail_window import TailDecisionWindow, TraceWindowState
from sampling.tail import TailSampler, TailRule

class FakeClock:
    def __init__(self, start_time: float = 100.0):
        self.cur = start_time
    def now(self) -> float:
        return self.cur
    def advance(self, s: float):
        self.cur += s

def test_TRC_096_tail_decision_window():
    clock = FakeClock()
    sampler = TailSampler(rules=[TailRule.error_filter()], default_rate=0.0)

    # Decision window: 10.0s, late span grace window: 20.0s
    window = TailDecisionWindow(
        decision_window_seconds=10.0,
        late_span_window_seconds=20.0,
        sampler=sampler,
        clock_fn=clock.now
    )

    # 1. Add root span for trace t1 at t=100s
    assert window.add_span(trace_id="t1", span_id="s1", status_code="OK", start_time_ns=1000, duration_ns=100) is True
    assert window.get_trace_state("t1") == TraceWindowState.BUFFERING

    # 2. Add late span inside decision window at t=105s (before 10s window closes)
    clock.advance(5.0)
    assert window.add_span(trace_id="t1", span_id="s2", status_code="ERROR", start_time_ns=1000, duration_ns=100) is True
    # Verify late span attached to trace t1
    trace_t1 = window.get_buffered_trace("t1")
    assert len(trace_t1.spans) == 2

    # 3. Advance clock past 10s (t=111s) -> evaluate ready traces
    clock.advance(6.0)
    decided = window.evaluate_ready_traces()
    # t1 had an error span attached during window -> sampled!
    assert "t1" in [t.trace_id for t in decided]
    assert window.get_trace_state("t1") == TraceWindowState.SAMPLED

    # 4. Late span arrives after decision for sampled trace inside late span grace window
    clock.advance(5.0)  # t=116s (<= 120s grace period)
    late_span_accepted = window.add_span(trace_id="t1", span_id="s3", status_code="OK", start_time_ns=1000, duration_ns=100)
    assert late_span_accepted is True # Late span accepted and marked for export

    # 5. Non-sampled trace evaluation
    window.add_span(trace_id="t2", span_id="s_ok", status_code="OK", start_time_ns=1000, duration_ns=100)
    clock.advance(11.0) # Decision window passes
    decided2 = window.evaluate_ready_traces()
    assert "t2" not in [t.trace_id for t in decided2]
    assert window.get_trace_state("t2") == TraceWindowState.DROPPED
