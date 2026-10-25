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
async def test_TRC_081_sorting():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = 1_700_000_000_000_000_000

    # Create 3 traces with known durations and timestamps
    # t1: start now, duration 100ms
    # t2: start now + 10s, duration 500ms
    # t3: start now + 20s, duration 200ms
    t1 = uuid.uuid4().hex
    t2 = uuid.uuid4().hex
    t3 = uuid.uuid4().hex

    spans = [
        make_span(tenant, t1, "op1", "svc", now, 100_000_000),
        make_span(tenant, t2, "op2", "svc", now + 10_000_000_000, 500_000_000),
        make_span(tenant, t3, "op3", "svc", now + 20_000_000_000, 200_000_000),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Sort by duration asc (t1: 100ms, t3: 200ms, t2: 500ms)
        asc_dur = await searcher.search_traces(
            session=session, tenant_id=tenant, order_by="duration", order_dir="asc"
        )
        assert [r.trace_id for r in asc_dur] == [t1, t3, t2]

        # Sort by duration desc (t2: 500ms, t3: 200ms, t1: 100ms)
        desc_dur = await searcher.search_traces(
            session=session, tenant_id=tenant, order_by="duration", order_dir="desc"
        )
        assert [r.trace_id for r in desc_dur] == [t2, t3, t1]

        # Sort by start_time asc (t1, t2, t3)
        asc_time = await searcher.search_traces(
            session=session, tenant_id=tenant, order_by="start_time", order_dir="asc"
        )
        assert [r.trace_id for r in asc_time] == [t1, t2, t3]

        # Sort by start_time desc (t3, t2, t1)
        desc_time = await searcher.search_traces(
            session=session, tenant_id=tenant, order_by="start_time", order_dir="desc"
        )
        assert [r.trace_id for r in desc_time] == [t3, t2, t1]
