import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns):
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
        status_code="OK",
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_079_trace_pagination():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()

    # Create 10 traces
    trace_ids = [uuid.uuid4().hex for _ in range(10)]
    spans = [
        make_span(tenant, tid, "op", "svc", now + i * 10_000_000, 5_000_000)
        for i, tid in enumerate(trace_ids)
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Page 1: first 5
        page1 = await searcher.search_traces(session=session, tenant_id=tenant, limit=5, offset=0)
        assert len(page1) == 5

        # Page 2: next 5
        page2 = await searcher.search_traces(session=session, tenant_id=tenant, limit=5, offset=5)
        assert len(page2) == 5

        # No overlap between pages
        page1_ids = {r.trace_id for r in page1}
        page2_ids = {r.trace_id for r in page2}
        assert page1_ids.isdisjoint(page2_ids)

        # All 10 traces accounted for
        all_ids = page1_ids | page2_ids
        for tid in trace_ids:
            assert tid in all_ids

        # Page 3: empty (offset 10 returns nothing)
        page3 = await searcher.search_traces(session=session, tenant_id=tenant, limit=5, offset=10)
        assert len(page3) == 0
