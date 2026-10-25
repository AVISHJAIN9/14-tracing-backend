import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_trace_search_operation_filter():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_get = uuid.uuid4().hex
    trace_post = uuid.uuid4().hex
    now_ns = time.time_ns()

    span1 = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_get,
        span_id=uuid.uuid4().hex[:16],
        service_name="api-gateway",
        name="GET /users",
        kind="SERVER",
        start_time_unix_nano=now_ns,
        end_time_unix_nano=now_ns + 10_000_000,
        duration_nanos=10_000_000,
        status_code="OK",
        attributes={}
    )
    span2 = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_post,
        span_id=uuid.uuid4().hex[:16],
        service_name="api-gateway",
        name="POST /orders",
        kind="SERVER",
        start_time_unix_nano=now_ns + 10_000_000,
        end_time_unix_nano=now_ns + 30_000_000,
        duration_nanos=20_000_000,
        status_code="OK",
        attributes={}
    )

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([span1, span2])
        await session.flush()

        searcher = TraceSearchService()

        # Search filtering by operation "GET /users"
        results_get = await searcher.search_traces(
            session=session,
            tenant_id=tenant,
            operation_name="GET /users"
        )
        assert len(results_get) == 1
        assert results_get[0].trace_id == trace_get
        assert results_get[0].root_name == "GET /users"

        # Search filtering by operation "POST /orders"
        results_post = await searcher.search_traces(
            session=session,
            tenant_id=tenant,
            operation_name="POST /orders"
        )
        assert len(results_post) == 1
        assert results_post[0].trace_id == trace_post
        assert results_post[0].root_name == "POST /orders"

        # Non-matching operation returns empty
        results_empty = await searcher.search_traces(
            session=session,
            tenant_id=tenant,
            operation_name="DELETE /items"
        )
        assert len(results_empty) == 0
