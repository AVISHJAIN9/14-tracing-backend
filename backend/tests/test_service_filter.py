import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_trace_search_service_filter():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_auth = uuid.uuid4().hex
    trace_billing = uuid.uuid4().hex
    now_ns = time.time_ns()

    span1 = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_auth,
        span_id=uuid.uuid4().hex[:16],
        service_name="auth-service",
        name="login",
        kind="SERVER",
        start_time_unix_nano=now_ns,
        end_time_unix_nano=now_ns + 5_000_000,
        duration_nanos=5_000_000,
        status_code="OK",
        attributes={}
    )
    span2 = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_billing,
        span_id=uuid.uuid4().hex[:16],
        service_name="billing-service",
        name="charge",
        kind="SERVER",
        start_time_unix_nano=now_ns + 10_000_000,
        end_time_unix_nano=now_ns + 25_000_000,
        duration_nanos=15_000_000,
        status_code="OK",
        attributes={}
    )

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all([span1, span2])
        await session.flush()

        searcher = TraceSearchService()

        # Search filtering by auth-service
        auth_results = await searcher.search_traces(
            session=session,
            tenant_id=tenant,
            service_name="auth-service"
        )

        assert len(auth_results) == 1
        assert auth_results[0].trace_id == trace_auth
        assert auth_results[0].root_service == "auth-service"

        # Search filtering by billing-service
        billing_results = await searcher.search_traces(
            session=session,
            tenant_id=tenant,
            service_name="billing-service"
        )

        assert len(billing_results) == 1
        assert billing_results[0].trace_id == trace_billing
        assert billing_results[0].root_service == "billing-service"

        # Non-existent service returns empty
        empty_results = await searcher.search_traces(
            session=session,
            tenant_id=tenant,
            service_name="unknown-service"
        )
        assert len(empty_results) == 0
