"""
Tail-sampling Decision Window.
Manages trace lifecycle through BUFFERING, SAMPLED, and DROPPED states.
Guarantees:
- Spans arriving inside the decision window attach to the buffered trace.
- When decision window expires, evaluates tail sampling policies.
- Late spans arriving after decision within the late span grace window are handled
  consistently (forwarded if sampled, dropped if dropped).
"""

import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from .tail import TailSampler
from .tail_buffer import BufferedSpan, BufferedTrace

class TraceWindowState(Enum):
    BUFFERING = "BUFFERING"
    SAMPLED = "SAMPLED"
    DROPPED = "DROPPED"

@dataclass
class WindowedTrace:
    trace: BufferedTrace
    state: TraceWindowState = TraceWindowState.BUFFERING
    decision_time: Optional[float] = None
    late_spans: List[BufferedSpan] = field(default_factory=list)

class TailDecisionWindow:
    def __init__(
        self,
        decision_window_seconds: float = 10.0,
        late_span_window_seconds: float = 30.0,
        sampler: Optional[TailSampler] = None,
        clock_fn: Optional[Callable[[], float]] = None
    ):
        self.decision_window_seconds = decision_window_seconds
        self.late_span_window_seconds = late_span_window_seconds
        self.sampler = sampler or TailSampler()
        self.clock_fn = clock_fn or time.time
        self.lock = threading.Lock()

        # trace_id -> WindowedTrace
        self.traces: Dict[str, WindowedTrace] = {}

    def get_trace_state(self, trace_id: str) -> Optional[TraceWindowState]:
        with self.lock:
            if trace_id in self.traces:
                return self.traces[trace_id].state
            return None

    def get_buffered_trace(self, trace_id: str) -> Optional[BufferedTrace]:
        with self.lock:
            if trace_id in self.traces:
                return self.traces[trace_id].trace
            return None

    def add_span(
        self,
        trace_id: str,
        span_id: str,
        status_code: str = "OK",
        start_time_ns: int = 0,
        duration_ns: int = 0,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        now = self.clock_fn()
        span = BufferedSpan(
            span_id=span_id,
            status_code=status_code,
            start_time_ns=start_time_ns,
            duration_ns=duration_ns,
            attributes=dict(attributes or {})
        )

        with self.lock:
            if trace_id not in self.traces:
                buffered = BufferedTrace(trace_id=trace_id, first_seen_time=now, spans=[span])
                self.traces[trace_id] = WindowedTrace(trace=buffered, state=TraceWindowState.BUFFERING)
                return True

            wtrace = self.traces[trace_id]

            # If still within decision window (BUFFERING)
            if wtrace.state == TraceWindowState.BUFFERING:
                wtrace.trace.spans.append(span)
                return True

            # If already decided SAMPLED: check if inside late span window
            if wtrace.state == TraceWindowState.SAMPLED:
                elapsed_since_first = now - wtrace.trace.first_seen_time
                if elapsed_since_first <= (self.decision_window_seconds + self.late_span_window_seconds):
                    wtrace.late_spans.append(span)
                    return True
                return False

            # If already DROPPED
            return False

    def evaluate_ready_traces(self) -> List[BufferedTrace]:
        now = self.clock_fn()
        ready_to_evaluate: List[WindowedTrace] = []

        with self.lock:
            # Find buffering traces where decision window has passed
            for tid, wtrace in self.traces.items():
                if wtrace.state == TraceWindowState.BUFFERING:
                    elapsed = now - wtrace.trace.first_seen_time
                    if elapsed >= self.decision_window_seconds:
                        ready_to_evaluate.append(wtrace)

        sampled_results: List[BufferedTrace] = []
        for wtrace in ready_to_evaluate:
            span_dicts = [
                {
                    "span_id": s.span_id,
                    "status_code": s.status_code,
                    "duration_nanos": s.duration_ns,
                    "attributes": s.attributes
                }
                for s in wtrace.trace.spans
            ]
            res = self.sampler.should_sample_trace(
                trace_id=wtrace.trace.trace_id,
                spans=span_dicts,
                trace_duration_ns=wtrace.trace.duration_ns
            )

            with self.lock:
                wtrace.decision_time = now
                if res.is_sampled:
                    wtrace.state = TraceWindowState.SAMPLED
                    sampled_results.append(wtrace.trace)
                else:
                    wtrace.state = TraceWindowState.DROPPED

        return sampled_results
