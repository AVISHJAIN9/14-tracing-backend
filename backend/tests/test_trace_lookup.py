import uuid
import pytest
from query.trace_lookup import TraceLookupService
from storage.db import get_db_session
from storage.models import SpanRecord

@pytest.mark.asyncio
async def test_trace_lookup_by_id():
    service = TraceLookupService()
    tenant_a = f"tenant-{uuid.uuid4().hex[:8]}"
    tenant_b = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    root_id = uuid.uuid4().hex[:16]
    child_id = uuid.uuid4().hex[:16]
    grandchild_id = uuid.uuid4().hex[:16]

    # Create a 3-tier distributed trace hierarchy
    spans = [
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=trace_id,
            span_id=root_id,
            parent_span_id=None,
            name="GET /checkout",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000300000000,  # 300ms
            duration_nanos=300000000,
            status_code="OK",
            status_message=None,
            attributes={"http.status_code": 200},
            events=[],
            links=[],
            service_name="api-gateway"
        ),
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=trace_id,
            span_id=child_id,
            parent_span_id=root_id,
            name="POST /payments/charge",
            kind="CLIENT",
            start_time_unix_nano=1700000000050000000,
            end_time_unix_nano=1700000000250000000,  # 200ms
            duration_nanos=200000000,
            status_code="OK",
            status_message=None,
            attributes={"peer.service": "payments"},
            events=[],
            links=[],
            service_name="api-gateway"
        ),
        SpanRecord(
            tenant_id=tenant_a,
            trace_id=trace_id,
            span_id=grandchild_id,
            parent_span_id=child_id,
            name="CHARGE_CARD",
            kind="SERVER",
            start_time_unix_nano=1700000000060000000,
            end_time_unix_nano=1700000000240000000,  # 180ms
            duration_nanos=180000000,
            status_code="ERROR",
            status_message="Card limit reached",
            attributes={"card.vendor": "visa"},
            events=[],
            links=[],
            service_name="payments-service"
        ),
    ]

    async with get_db_session(tenant_id=tenant_a) as session:
        session.add_all(spans)
        await session.flush()

    # 1. Lookup by ID under tenant A
    async with get_db_session(tenant_id=tenant_a) as session:
        trace_view = await service.get_trace_by_id(session, tenant_a, trace_id)
        assert trace_view is not None
        assert trace_view.trace_id == trace_id
        assert trace_view.root_span_id == root_id
        assert trace_view.total_spans == 3
        assert trace_view.has_errors is True
        assert trace_view.duration_nanos == 300000000
        assert trace_view.services == {"api-gateway", "payments-service"}
        assert len(trace_view.spans) == 3
        assert [s["span_id"] for s in trace_view.spans] == [root_id, child_id, grandchild_id]

    # 2. Cross-tenant isolation check: tenant B cannot lookup tenant A's trace
    async with get_db_session(tenant_id=tenant_b) as session:
        cross_trace = await service.get_trace_by_id(session, tenant_b, trace_id)
        assert cross_trace is None

    # 3. Non-existent trace returns None
    async with get_db_session(tenant_id=tenant_a) as session:
        missing = await service.get_trace_by_id(session, tenant_a, uuid.uuid4().hex)
        assert missing is None

    # 4. Invalid trace_id format raises ValueError
    async with get_db_session(tenant_id=tenant_a) as session:
        with pytest.raises(ValueError, match="Invalid trace_id"):
            await service.get_trace_by_id(session, tenant_a, "invalid-trace-id")
