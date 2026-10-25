import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord
from observability.profiler import LatencyBenchmarker

@pytest.mark.asyncio
async def test_TRC_131_latency_benchmarking():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    # Seed 10 spans
    spans = [
        SpanRecord(
            tenant_id=tenant,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            service_name="bench-svc",
            name=f"bench_op_{i}",
            kind="SERVER",
            start_time_unix_nano=now + i * 1_000,
            end_time_unix_nano=now + (i + 1) * 1_000,
            duration_nanos=1_000,
            status_code="OK",
            attributes={},
            events=[],
            links=[]
        )
        for i in range(10)
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    latencies = []
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run 30 sequential API requests to collect latency measurements
        for _ in range(30):
            t0 = time.perf_counter()
            res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
            lat = (time.perf_counter() - t0) * 1000.0
            assert res.status_code == 200
            latencies.append(lat)

    stats = LatencyBenchmarker.compute_percentiles(latencies)
    assert stats.count == 30
    assert stats.min_ms > 0
    assert stats.max_ms >= stats.min_ms
    assert stats.p50_ms >= stats.min_ms
    assert stats.p95_ms >= stats.p50_ms
    assert stats.p99_ms >= stats.p95_ms
    # Verify local endpoint latency target (p95 under 250ms)
    assert stats.p95_ms < 250.0
