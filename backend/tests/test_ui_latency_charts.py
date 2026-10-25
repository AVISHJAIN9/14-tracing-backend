import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, start_ns, duration_ns):
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="latency-svc",
        name="op",
        kind="SERVER",
        start_time_unix_nano=start_ns,
        end_time_unix_nano=start_ns + duration_ns,
        duration_nanos=duration_ns,
        status_code="OK",
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_118_latency_charts():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()
    durations = [10_000_000, 25_000_000, 50_000_000, 100_000_000, 250_000_000]

    spans = [
        make_span(tenant, uuid.uuid4().hex, now + i * 1_000_000, dur)
        for i, dur in enumerate(durations)
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/traces/search", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        traces = res.json()["traces"]
        assert len(traces) == 5

        # Compute latency distribution percentiles
        trace_durations_ms = sorted(t["duration_nanos"] / 1_000_000 for t in traces)
        p50 = trace_durations_ms[2]
        p90 = trace_durations_ms[4]
        assert p50 == 50.0
        assert p90 == 250.0
