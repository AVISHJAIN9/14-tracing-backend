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
async def test_TRC_074_duration_filter():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t_short = uuid.uuid4().hex   # 5ms
    t_medium = uuid.uuid4().hex  # 50ms
    t_long = uuid.uuid4().hex    # 500ms
    now = time.time_ns()

    spans = [
        make_span(tenant, t_short, "op", "svc", now, 5_000_000),
        make_span(tenant, t_medium, "op", "svc", now + 1_000_000_000, 50_000_000),
        make_span(tenant, t_long, "op", "svc", now + 2_000_000_000, 500_000_000),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # min only: >= 10ms
        results = await searcher.search_traces(session=session, tenant_id=tenant, min_duration_ns=10_000_000)
        ids = {r.trace_id for r in results}
        assert t_medium in ids
        assert t_long in ids
        assert t_short not in ids

        # max only: <= 60ms
        results = await searcher.search_traces(session=session, tenant_id=tenant, max_duration_ns=60_000_000)
        ids = {r.trace_id for r in results}
        assert t_short in ids
        assert t_medium in ids
        assert t_long not in ids

        # range: [10ms, 60ms]
        results = await searcher.search_traces(session=session, tenant_id=tenant,
                                               min_duration_ns=10_000_000, max_duration_ns=60_000_000)
        ids = {r.trace_id for r in results}
        assert t_medium in ids
        assert t_short not in ids
        assert t_long not in ids
