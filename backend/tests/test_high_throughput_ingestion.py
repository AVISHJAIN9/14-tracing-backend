import uuid
import time
import pytest
from storage.db import get_db_session
from storage.models import SpanRecord
from collector.throughput_engine import ThroughputIngestionEngine

@pytest.mark.asyncio
async def test_TRC_125_high_throughput_ingestion():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    engine = ThroughputIngestionEngine(default_batch_size=200)

    # Generate 500 spans to benchmark ingestion throughput
    now = time.time_ns()
    spans = []
    for i in range(500):
        span = SpanRecord(
            tenant_id=tenant,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            service_name=f"svc-{i % 5}",
            name=f"operation_{i}",
            kind="INTERNAL",
            start_time_unix_nano=now + i * 10_000,
            end_time_unix_nano=now + i * 10_000 + 50_000,
            duration_nanos=50_000,
            status_code="OK",
            attributes={"batch.index": i, "cluster": "us-east-1"},
            events=[],
            links=[]
        )
        spans.append(span)

    async with get_db_session(tenant_id=tenant) as session:
        result = await engine.ingest_batch(session, tenant, spans, batch_size=200)

    assert result.total_spans == 500
    assert result.batch_count == 3  # 200 + 200 + 100
    assert result.duration_seconds > 0
    assert result.spans_per_second > 100  # Expect high throughput
    assert result.p95_batch_latency_ms >= 0
