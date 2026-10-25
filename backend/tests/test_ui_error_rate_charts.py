import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, service, status):
    now = time.time_ns()
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name=service,
        name="op",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 10_000_000,
        duration_nanos=10_000_000,
        status_code=status,
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_119_error_rate_charts():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"

    # Insert 4 OK traces, 2 ERROR traces
    spans = [
        make_span(tenant, uuid.uuid4().hex, "web-api", "OK"),
        make_span(tenant, uuid.uuid4().hex, "web-api", "OK"),
        make_span(tenant, uuid.uuid4().hex, "web-api", "OK"),
        make_span(tenant, uuid.uuid4().hex, "web-api", "OK"),
        make_span(tenant, uuid.uuid4().hex, "billing-svc", "ERROR"),
        make_span(tenant, uuid.uuid4().hex, "billing-svc", "ERROR"),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/traces/search", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        traces = res.json()["traces"]
        assert len(traces) == 6

        error_traces = sum(1 for t in traces if t["has_errors"])
        assert error_traces == 2
        error_rate = error_traces / len(traces)
        assert pytest.approx(error_rate, rel=1e-3) == (2.0 / 6.0)
