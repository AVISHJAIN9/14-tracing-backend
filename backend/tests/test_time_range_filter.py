import uuid
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
async def test_TRC_076_time_range_filter():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    # Use fixed base times for predictable range testing
    base_ns = 1_700_000_000_000_000_000  # fixed epoch in nanoseconds
    t_early = uuid.uuid4().hex    # starts at base
    t_mid   = uuid.uuid4().hex    # starts at base + 100ms
    t_late  = uuid.uuid4().hex    # starts at base + 500ms

    spans = [
        make_span(tenant, t_early, "op", "svc", base_ns, 10_000_000),
        make_span(tenant, t_mid,   "op", "svc", base_ns + 100_000_000, 10_000_000),
        make_span(tenant, t_late,  "op", "svc", base_ns + 500_000_000, 10_000_000),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # window: [base, base+200ms] — should get early and mid
        results = await searcher.search_traces(
            session=session, tenant_id=tenant,
            min_time_ns=base_ns,
            max_time_ns=base_ns + 200_000_000
        )
        ids = {r.trace_id for r in results}
        assert t_early in ids
        assert t_mid in ids
        assert t_late not in ids

        # window: [base+200ms, base+600ms] — should get late only
        results = await searcher.search_traces(
            session=session, tenant_id=tenant,
            min_time_ns=base_ns + 200_000_000,
            max_time_ns=base_ns + 600_000_000
        )
        ids = {r.trace_id for r in results}
        assert t_late in ids
        assert t_early not in ids
        assert t_mid not in ids
