import uuid
import pytest
from sqlalchemy import select, func
from collector.idempotent_ingest import IdempotentSpanIngester
from storage.db import get_db_session
from storage.models import SpanRecord
from security.tenant import TenantService

@pytest.mark.asyncio
async def test_duplicate_batch_redelivery_idempotent():
    ingester = IdempotentSpanIngester()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex

    # Create 10 spans
    spans = [
        SpanRecord(
            tenant_id=tid,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name=f"idempotent-op-{i}",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000 + i * 1000,
            end_time_unix_nano=1700000000000000000 + (i + 1) * 1000,
            duration_nanos=1000,
            status_code="OK",
            status_message=None,
            attributes={"attempt": 1},
            events=[],
            links=[],
            service_name="payment-service"
        )
        for i in range(10)
    ]

    # First delivery
    async with get_db_session(tenant_id=tid) as session:
        inserted1 = await ingester.ingest_spans_idempotent(session, tid, spans)
        assert inserted1 == 10

    # Verify 10 rows in PostgreSQL
    async with get_db_session(tenant_id=tid) as session:
        stored1 = await TenantService.get_spans_for_tenant(session, tid, trace_id)
        assert len(stored1) == 10

    # Second delivery: EXACT same batch redelivered (Scenario S14-03)
    async with get_db_session(tenant_id=tid) as session:
        inserted2 = await ingester.ingest_spans_idempotent(session, tid, spans)
        assert inserted2 >= 0  # Re-delivery handled cleanly without crash

    # Verify STILL exactly 10 rows (no duplicates created)
    async with get_db_session(tenant_id=tid) as session:
        result = await session.execute(
            select(func.count()).select_from(SpanRecord).where(
                SpanRecord.tenant_id == tid,
                SpanRecord.trace_id == trace_id
            )
        )
        total_count = result.scalar_one()
        assert total_count == 10
