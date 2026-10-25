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
async def test_TRC_075_status_filter():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t_ok = uuid.uuid4().hex
    t_error = uuid.uuid4().hex
    t_unset = uuid.uuid4().hex
    now = time.time_ns()

    spans = [
        make_span(tenant, t_ok, "op", "svc", now, 10_000_000, "OK"),
        make_span(tenant, t_error, "op", "svc", now + 1_000_000_000, 10_000_000, "ERROR"),
        make_span(tenant, t_unset, "op", "svc", now + 2_000_000_000, 10_000_000, "UNSET"),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        ok_results = await searcher.search_traces(session=session, tenant_id=tenant, status_code="OK")
        ok_ids = {r.trace_id for r in ok_results}
        assert t_ok in ok_ids
        assert t_error not in ok_ids
        assert t_unset not in ok_ids

        error_results = await searcher.search_traces(session=session, tenant_id=tenant, status_code="ERROR")
        error_ids = {r.trace_id for r in error_results}
        assert t_error in error_ids
        assert t_ok not in error_ids

        unset_results = await searcher.search_traces(session=session, tenant_id=tenant, status_code="UNSET")
        unset_ids = {r.trace_id for r in unset_results}
        assert t_unset in unset_ids
        assert t_ok not in unset_ids
