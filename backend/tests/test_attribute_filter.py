import uuid
import time
import pytest
from query.trace_search import TraceSearchService
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, name, service, start_ns, duration_ns, status="OK", attributes=None):
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
        attributes=attributes or {}
    )

@pytest.mark.asyncio
async def test_TRC_077_attribute_filter():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    t_http = uuid.uuid4().hex
    t_grpc = uuid.uuid4().hex
    t_none = uuid.uuid4().hex
    now = time.time_ns()

    spans = [
        make_span(tenant, t_http, "op", "svc", now, 10_000_000, attributes={"http.method": "GET", "http.status_code": "200"}),
        make_span(tenant, t_grpc, "op", "svc", now + 1_000_000_000, 10_000_000, attributes={"rpc.system": "grpc", "rpc.method": "SayHello"}),
        make_span(tenant, t_none, "op", "svc", now + 2_000_000_000, 10_000_000, attributes={}),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

        searcher = TraceSearchService()

        # Filter by attribute key=value
        http_results = await searcher.search_traces(
            session=session, tenant_id=tenant,
            attribute_filter={"http.method": "GET"}
        )
        ids = {r.trace_id for r in http_results}
        assert t_http in ids
        assert t_grpc not in ids
        assert t_none not in ids

        # Filter by grpc attribute
        grpc_results = await searcher.search_traces(
            session=session, tenant_id=tenant,
            attribute_filter={"rpc.system": "grpc"}
        )
        ids = {r.trace_id for r in grpc_results}
        assert t_grpc in ids
        assert t_http not in ids

        # Non-matching attribute returns empty
        empty = await searcher.search_traces(
            session=session, tenant_id=tenant,
            attribute_filter={"db.system": "mysql"}
        )
        assert len(empty) == 0
