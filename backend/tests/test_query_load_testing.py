import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord
from storage.load_harness import LoadTestingHarness

@pytest.mark.asyncio
async def test_TRC_130_query_load_testing():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    # Seed 20 spans under the test trace
    spans = [
        SpanRecord(
            tenant_id=tenant,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            service_name="api-gateway",
            name=f"query_load_test_{i}",
            kind="SERVER",
            start_time_unix_nano=now + i * 1_000,
            end_time_unix_nano=now + (i + 1) * 1_000,
            duration_nanos=1_000,
            status_code="OK",
            attributes={"service.load": True},
            events=[],
            links=[]
        )
        for i in range(20)
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async def _query_trace():
            res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
            return res.status_code == 200 and len(res.json()["spans"]) == 20

        summary = await LoadTestingHarness.run_concurrent_query_load(
            query_fn=_query_trace,
            total_queries=25,
            concurrency=5
        )

        assert summary.total_operations == 25
        assert summary.error_count == 0
        assert summary.p50_latency_ms > 0
        assert summary.p95_latency_ms < 500.0  # Under 500ms even under concurrency
        assert summary.ops_per_second > 10.0
