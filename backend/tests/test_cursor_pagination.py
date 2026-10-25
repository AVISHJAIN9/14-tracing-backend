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
async def test_TRC_080_cursor_pagination():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    base_time = 1_700_000_000_000_000_000

    # Create 8 traces with distinct timestamps
    trace_ids = [f"{i:032x}" for i in range(1, 9)]
    spans = [
        make_span(tenant, tid, f"op-{i}", "svc", base_time + i * 1_000_000_000, 10_000_000)
        for i, tid in enumerate(trace_ids)
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Fetch page 1 (limit 3) with cursor pagination
        p1_res, next_cursor = await searcher.search_traces_cursor(
            session=session, tenant_id=tenant, limit=3, cursor=None
        )
        assert len(p1_res) == 3
        assert next_cursor is not None

        # Fetch page 2 (limit 3) using next_cursor
        p2_res, next_cursor2 = await searcher.search_traces_cursor(
            session=session, tenant_id=tenant, limit=3, cursor=next_cursor
        )
        assert len(p2_res) == 3
        assert next_cursor2 is not None

        # Fetch page 3 (limit 3)
        p3_res, next_cursor3 = await searcher.search_traces_cursor(
            session=session, tenant_id=tenant, limit=3, cursor=next_cursor2
        )
        assert len(p3_res) == 2
        assert next_cursor3 is None  # Reached the end

        # Ensure no duplicates across pages
        p1_ids = {r.trace_id for r in p1_res}
        p2_ids = {r.trace_id for r in p2_res}
        p3_ids = {r.trace_id for r in p3_res}
        assert p1_ids.isdisjoint(p2_ids)
        assert p2_ids.isdisjoint(p3_ids)
        assert p1_ids.isdisjoint(p3_ids)
        assert (p1_ids | p2_ids | p3_ids) == set(trace_ids)
