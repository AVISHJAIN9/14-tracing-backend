import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord
from collector.large_trace import LargeTraceAnalyzer

@pytest.mark.asyncio
async def test_TRC_127_large_trace_testing():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    total_spans = 250
    root_id = uuid.uuid4().hex[:16]

    # Create root span
    root = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=root_id,
        parent_span_id=None,
        service_name="orchestrator",
        name="root_job",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 500_000_000,
        duration_nanos=500_000_000,
        status_code="OK",
        attributes={"large_trace.total": total_spans},
        events=[],
        links=[]
    )

    spans = [root]
    # Chain and fan-out 249 descendant spans
    curr_parent = root_id
    for i in range(1, total_spans):
        sid = uuid.uuid4().hex[:16]
        # Alternate between branching and chaining
        pid = curr_parent if i % 2 == 0 else root_id
        if i % 10 == 0:
            curr_parent = sid

        spans.append(
            SpanRecord(
                tenant_id=tenant,
                trace_id=trace_id,
                span_id=sid,
                parent_span_id=pid,
                service_name=f"worker-{i % 8}",
                name=f"step_{i}",
                kind="INTERNAL",
                start_time_unix_nano=now + i * 1_000_000,
                end_time_unix_nano=now + (i + 1) * 1_000_000,
                duration_nanos=1_000_000,
                status_code="OK",
                attributes={"step.index": i},
                events=[],
                links=[]
            )
        )

    # Topological analysis check
    topology = LargeTraceAnalyzer.analyze_trace_topology(spans)
    assert topology["total_spans"] == total_spans
    assert topology["max_depth"] > 1
    assert topology["max_fan_out"] > 1
    assert topology["root_spans"] == 1
    assert len(topology["services"]) >= 5

    # Persist large trace
    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    # Query trace through real API
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        assert data["trace_id"] == trace_id
        assert data["span_count"] == total_spans
        assert len(data["spans"]) == total_spans
