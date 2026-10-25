import uuid
import time
from storage.models import SpanRecord
from observability.profiler import MemoryProfiler

def test_TRC_132_memory_profiling():
    now = time.time_ns()
    item_count = 500

    def _allocate_spans():
        records = []
        for i in range(item_count):
            rec = SpanRecord(
                tenant_id="mem-test-tenant",
                trace_id=f"t_{i:014d}",
                span_id=f"s_{i:014d}",
                service_name="profiled-service",
                name="profiled_span_operation",
                kind="INTERNAL",
                start_time_unix_nano=now + i * 1_000,
                end_time_unix_nano=now + (i + 1) * 1_000,
                duration_nanos=1_000,
                status_code="OK",
                attributes={"alloc.id": i, "profiler.mode": "tracemalloc"},
                events=[{"name": "checkpoint", "time_unix_nano": now + i * 1_000}],
                links=[]
            )
            records.append(rec)
        return records

    records, report = MemoryProfiler.profile_execution(_allocate_spans, item_count=item_count)

    assert len(records) == item_count
    assert report.peak_kib > 0
    assert report.net_allocated_kib > 0
    # Average span memory allocation footprint should be bounded (under 10 KiB per model object)
    assert report.avg_kib_per_item < 10.0
