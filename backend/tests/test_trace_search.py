import uuid
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_trace_search_multi_tenant():
    service = TraceSearchService()
    tenant_a = f"tenant-{uuid.uuid4().hex[:8]}"
    tenant_b = f"tenant-{uuid.uuid4().hex[:8]}"

    t1 = uuid.uuid4().hex
    t2 = uuid.uuid4().hex
    t3 = uuid.uuid4().hex
    tb = uuid.uuid4().hex

    records = [
        # Trace 1 under Tenant A: 2 spans, OK
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=t1,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name="GET /items",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000100000000,
            duration_nanos=100000000,
            status_code="OK",
            service_name="catalog",
            attributes={}
        ),
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=t1,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name="db.query",
            kind="CLIENT",
            start_time_unix_nano=1700000000010000000,
            end_time_unix_nano=1700000000090000000,
            duration_nanos=80000000,
            status_code="OK",
            service_name="catalog",
            attributes={}
        ),
        # Trace 2 under Tenant A: 1 span, ERROR
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=t2,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name="POST /cart",
            kind="SERVER",
            start_time_unix_nano=1700000000200000000,
            end_time_unix_nano=1700000000300000000,
            duration_nanos=100000000,
            status_code="ERROR",
            service_name="cart",
            attributes={}
        ),
        # Trace 3 under Tenant A: 1 span, OK
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=t3,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name="GET /profile",
            kind="SERVER",
            start_time_unix_nano=1700000000400000000,
            end_time_unix_nano=1700000000450000000,
            duration_nanos=50000000,
            status_code="OK",
            service_name="user",
            attributes={}
        ),
        # Trace under Tenant B: should never be returned for Tenant A
        SpanRecord(
            tenant_id=tenant_b,
            trace_id=tb,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name="GET /secret",
            kind="SERVER",
            start_time_unix_nano=1700000000500000000,
            end_time_unix_nano=1700000000600000000,
            duration_nanos=100000000,
            status_code="OK",
            service_name="secret",
            attributes={}
        ),
    ]

    async with get_db_session(tenant_id=tenant_a) as session:
        session.add_all(records[:4])
        await session.flush()

    async with get_db_session(tenant_id=tenant_b) as session:
        session.add(records[4])
        await session.flush()

    # Search traces for Tenant A
    async with get_db_session(tenant_id=tenant_a) as session:
        results = await service.search_traces(session, tenant_a, limit=10, offset=0)
        assert len(results) == 3
        trace_ids = [r.trace_id for r in results]
        assert tb not in trace_ids
        assert set(trace_ids) == {t1, t2, t3}

        # Check trace 1 attributes
        t1_res = next(r for r in results if r.trace_id == t1)
        assert t1_res.span_count == 2
        assert t1_res.has_errors is False
        assert t1_res.duration_nanos == 100000000

        # Check trace 2 attributes (error)
        t2_res = next(r for r in results if r.trace_id == t2)
        assert t2_res.has_errors is True

        # Check pagination (limit=2, offset=1)
        paged = await service.search_traces(session, tenant_a, limit=2, offset=1)
        assert len(paged) == 2
