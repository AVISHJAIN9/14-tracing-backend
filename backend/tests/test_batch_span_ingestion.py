import uuid
import pytest
from sqlalchemy import select, func
from collector.otlp import OtlpIngestService
from storage.db import get_db_session
from storage.models import SpanRecord
from security.tenant import TenantService

@pytest.mark.asyncio
async def test_batch_span_ingestion_bulk_write():
    ingester = OtlpIngestService()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"

    # Generate 100 spans across 5 traces
    records = []
    traces = [uuid.uuid4().hex for _ in range(5)]
    for i in range(100):
        t_id = traces[i % len(traces)]
        s_id = uuid.uuid4().hex[:16]
        rec = SpanRecord(
            tenant_id=tid,
            trace_id=t_id,
            span_id=s_id,
            parent_span_id=None,
            name=f"batch-op-{i}",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000 + i * 1000,
            end_time_unix_nano=1700000000000000000 + (i + 1) * 1000,
            duration_nanos=1000,
            status_code="OK",
            status_message=None,
            attributes={"batch.index": i, "worker": "collector-batch"},
            events=[],
            links=[],
            service_name=f"service-{i % 3}"
        )
        records.append(rec)

    # Ingest using batch_ingest_records
    async with get_db_session(tenant_id=tid) as session:
        count = await ingester.batch_ingest_records(session, tid, records, batch_size=25)
        assert count == 100

    # Verify counts in PostgreSQL 16
    async with get_db_session(tenant_id=tid) as session:
        result = await session.execute(
            select(func.count()).select_from(SpanRecord).where(SpanRecord.tenant_id == tid)
        )
        total_spans = result.scalar_one()
        assert total_spans == 100

        # Verify trace retrieval
        spans_trace0 = await TenantService.get_spans_for_tenant(session, tid, traces[0])
        assert len(spans_trace0) == 20
