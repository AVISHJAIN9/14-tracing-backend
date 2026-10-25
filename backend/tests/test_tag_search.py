import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns, attributes=None):
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
        attributes=attributes or {}
    )

@pytest.mark.asyncio
async def test_TRC_078_tag_search():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t_tagged = uuid.uuid4().hex
    t_other = uuid.uuid4().hex
    now = time.time_ns()

    spans = [
        make_span(tenant, t_tagged, "op", "svc", now, 10_000_000, attributes={"env": "production", "version": "1.2.3"}),
        make_span(tenant, t_other, "op", "svc", now + 1_000_000_000, 10_000_000, attributes={"env": "staging"}),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Tag key existence search: traces that have attribute key "version"
        version_results = await searcher.search_traces(
            session=session, tenant_id=tenant,
            tag_key="version"
        )
        ids = {r.trace_id for r in version_results}
        assert t_tagged in ids
        assert t_other not in ids

        # Tag key "env" exists in both
        env_results = await searcher.search_traces(
            session=session, tenant_id=tenant,
            tag_key="env"
        )
        ids = {r.trace_id for r in env_results}
        assert t_tagged in ids
        assert t_other in ids

        # Non-existent tag key returns empty
        empty = await searcher.search_traces(
            session=session, tenant_id=tenant,
            tag_key="db.url"
        )
        assert len(empty) == 0
