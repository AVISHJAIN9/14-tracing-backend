import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns, status_msg=None):
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
        status_code="ERROR" if status_msg else "OK",
        status_message=status_msg,
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_082_fulltext_search():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    now = time.time_ns()

    t_payment = uuid.uuid4().hex
    t_checkout = uuid.uuid4().hex
    t_inventory = uuid.uuid4().hex

    spans = [
        make_span(tenant, t_payment, "process_payment_v2", "billing-service", now, 10_000_000, status_msg="Card network timeout"),
        make_span(tenant, t_checkout, "render_checkout_page", "frontend-gw", now + 1_000_000_000, 10_000_000),
        make_span(tenant, t_inventory, "reserve_stock", "warehouse-svc", now + 2_000_000_000, 10_000_000),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Query matches status_message ("timeout")
        res1 = await searcher.search_traces(session=session, tenant_id=tenant, query_text="timeout")
        ids1 = {r.trace_id for r in res1}
        assert t_payment in ids1
        assert t_checkout not in ids1
        assert t_inventory not in ids1

        # Query matches service name ("warehouse")
        res2 = await searcher.search_traces(session=session, tenant_id=tenant, query_text="warehouse")
        ids2 = {r.trace_id for r in res2}
        assert t_inventory in ids2
        assert t_payment not in ids2

        # Query matches operation name ("checkout")
        res3 = await searcher.search_traces(session=session, tenant_id=tenant, query_text="checkout")
        ids3 = {r.trace_id for r in res3}
        assert t_checkout in ids3

        # Non-matching query returns empty
        res4 = await searcher.search_traces(session=session, tenant_id=tenant, query_text="nonexistentterm123")
        assert len(res4) == 0
