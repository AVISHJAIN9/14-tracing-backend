"""
Latency Benchmarking, Memory Profiling, and CPU Profiling Utilities.
Provides deterministic performance measurement and diagnostic profiling for tracing workloads.
"""

import time
import tracemalloc
import cProfile
import pstats
import io
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Callable

@dataclass
class LatencyPercentiles:
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float

class LatencyBenchmarker:
    @staticmethod
    def compute_percentiles(durations_ms: List[float]) -> LatencyPercentiles:
        if not durations_ms:
            return LatencyPercentiles(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        sorted_dur = sorted(durations_ms)
        n = len(sorted_dur)

        def _p(pct: float) -> float:
            idx = int(math.ceil(pct * n)) - 1
            return sorted_dur[max(0, min(idx, n - 1))]

        return LatencyPercentiles(
            count=n,
            min_ms=sorted_dur[0],
            max_ms=sorted_dur[-1],
            mean_ms=sum(sorted_dur) / n,
            p50_ms=_p(0.50),
            p90_ms=_p(0.90),
            p95_ms=_p(0.95),
            p99_ms=_p(0.99)
        )

@dataclass
class MemoryProfileReport:
    initial_kib: float
    peak_kib: float
    net_allocated_kib: float
    avg_kib_per_item: float

class MemoryProfiler:
    @staticmethod
    def profile_execution(fn: Callable[[], Any], item_count: int = 1) -> tuple[Any, MemoryProfileReport]:
        tracemalloc.start()
        tracemalloc.reset_peak()
        init_size, _ = tracemalloc.get_traced_memory()

        result = fn()

        curr_size, peak_size = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        init_kib = init_size / 1024.0
        peak_kib = peak_size / 1024.0
        net_kib = (curr_size - init_size) / 1024.0
        per_item = max(net_kib, 0.0) / max(item_count, 1)

        report = MemoryProfileReport(
            initial_kib=init_kib,
            peak_kib=peak_kib,
            net_allocated_kib=net_kib,
            avg_kib_per_item=per_item
        )
        return result, report

@dataclass
class CpuProfileReport:
    total_time_seconds: float
    total_calls: int
    top_functions: List[str]

class CpuProfiler:
    @staticmethod
    def profile_execution(fn: Callable[[], Any], top_n: int = 5) -> tuple[Any, CpuProfileReport]:
        profiler = cProfile.Profile()
        profiler.enable()

        result = fn()

        profiler.disable()

        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
        ps.print_stats(top_n)

        # Extract stats
        output_lines = s.getvalue().splitlines()
        top_funcs = [line.strip() for line in output_lines if line.strip() and not line.startswith("ncalls")][:top_n]

        return result, CpuProfileReport(
            total_time_seconds=ps.total_tt,
            total_calls=ps.total_calls,
            top_functions=top_funcs
        )
