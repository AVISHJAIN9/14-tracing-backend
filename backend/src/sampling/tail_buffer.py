"""
Tail Sampling Buffer.
Buffers incoming spans by trace_id until a decision window expires or buffer capacity limits.
Evaluates tail sampling rules and flushes retained traces while dropping unsampled traces.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from .tail import TailSampler

@dataclass
class BufferedSpan:
    span_id: str
    status_code: str
    start_time_ns: int
    duration_ns: int
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BufferedTrace:
    trace_id: str
    first_seen_time: float
    spans: List[BufferedSpan] = field(default_factory=list)

    @property
    def duration_ns(self) -> int:
        if not self.spans:
            return 0
        min_start = min(s.start_time_ns for s in self.spans)
        max_end = max(s.start_time_ns + s.duration_ns for s in self.spans)
        return max(0, max_end - min_start)

class TailSamplingBuffer:
    def __init__(
        self,
        max_traces: int = 10000,
        decision_window_seconds: float = 30.0,
        sampler: Optional[TailSampler] = None,
        clock_fn: Optional[Callable[[], float]] = None
    ):
        self.max_traces = max_traces
        self.decision_window_seconds = decision_window_seconds
        self.sampler = sampler or TailSampler()
        self.clock_fn = clock_fn or time.time
        self.lock = threading.Lock()

        # trace_id -> BufferedTrace
        self.traces: Dict[str, BufferedTrace] = {}
        self.drop_count = 0

    @property
    def trace_count(self) -> int:
        with self.lock:
            return len(self.traces)

    def add_span(
        self,
        trace_id: str,
        span_id: str,
        status_code: str = "OK",
        start_time_ns: int = 0,
        duration_ns: int = 0,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        with self.lock:
            if trace_id not in self.traces:
                if len(self.traces) >= self.max_traces:
                    self.drop_count += 1
                    return False
                now = self.clock_fn()
                self.traces[trace_id] = BufferedTrace(trace_id=trace_id, first_seen_time=now)

            span = BufferedSpan(
                span_id=span_id,
                status_code=status_code,
                start_time_ns=start_time_ns,
                duration_ns=duration_ns,
                attributes=dict(attributes or {})
            )
            self.traces[trace_id].spans.append(span)
            return True

    def flush_ready_traces(self) -> List[BufferedTrace]:
        now = self.clock_fn()
        ready_traces: List[BufferedTrace] = []

        with self.lock:
            trace_ids_to_remove = []
            for tid, trace in self.traces.items():
                if (now - trace.first_seen_time) >= self.decision_window_seconds:
                    trace_ids_to_remove.append(tid)

            for tid in trace_ids_to_remove:
                ready_traces.append(self.traces.pop(tid))

        # Evaluate tail sampling decision on ready traces
        sampled_traces: List[BufferedTrace] = []
        for trace in ready_traces:
            span_dicts = [
                {
                    "span_id": s.span_id,
                    "status_code": s.status_code,
                    "duration_nanos": s.duration_ns,
                    "attributes": s.attributes
                }
                for s in trace.spans
            ]
            result = self.sampler.should_sample_trace(
                trace_id=trace.trace_id,
                spans=span_dicts,
                trace_duration_ns=trace.duration_ns
            )
            if result.is_sampled:
                sampled_traces.append(trace)

        return sampled_traces
