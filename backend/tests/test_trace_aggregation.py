import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns, status="OK"):
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name=service,
        name=name,
        kind="SERVER",
        start_time_unix_nano=start_ns,
        end_time_unix_nano=start_ns + duration_ns,
        duration_nanos=duration_ns,
        status_code=status,
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_083_trace_aggregation():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = 1_700_000_000_000_000_000

    # Trace 1: 100ms duration, OK, 2 spans
    t1 = uuid.uuid4().hex
    # Trace 2: 300ms duration, ERROR, 1 span
    t2 = uuid.uuid4().hex
    # Trace 3: 200ms duration, OK, 3 spans
    t3 = uuid.uuid4().hex

    spans = [
        # t1: 2 spans
        make_span(tenant, t1, "root", "api-gw", now, 100_000_000, "OK"),
        make_span(tenant, t1, "child", "auth-svc", now + 10_000_000, 50_000_000, "OK"),
        # t2: 1 span, ERROR
        make_span(tenant, t2, "root", "payment-svc", now + 1_000_000_000, 300_000_000, "ERROR"),
        # t3: 3 spans
        make_span(tenant, t3, "root", "api-gw", now + 2_000_000_000, 200_000_000, "OK"),
        make_span(tenant, t3, "child1", "db-svc", now + 2_010_000_000, 80_000_000, "OK"),
        make_span(tenant, t3, "child2", "cache-svc", now + 2_090_000_000, 20_000_000, "OK"),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Compute trace aggregations for this tenant
        agg = await searcher.aggregate_traces(session=session, tenant_id=tenant)

        assert agg.total_traces == 3
        assert agg.error_traces == 1
        assert pytest.approx(agg.error_rate, rel=1e-3) == (1.0 / 3.0)
        assert agg.total_spans == 6
        assert pytest.approx(agg.avg_spans_per_trace, rel=1e-3) == 2.0
        assert agg.min_duration_nanos == 100_000_000
        assert agg.max_duration_nanos == 300_000_000
        assert pytest.approx(agg.avg_duration_nanos, rel=1e-3) == 200_000_000.0

        # Filter aggregation by service_name
        agg_payment = await searcher.aggregate_traces(session=session, tenant_id=tenant, service_name="payment-svc")
        assert agg_payment.total_traces == 1
        assert agg_payment.error_traces == 1
        assert agg_payment.error_rate == 1.0
        assert agg_payment.total_spans == 1
