import uuid
import time
import pytest
from sqlalchemy import select, func
from storage.db import get_db_session
from storage.models import SpanRecord
from storage.load_harness import LoadTestingHarness

@pytest.mark.asyncio
async def test_TRC_129_storage_load_testing():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()
    batch_size = 50
    total_spans = 200

    async def _write_batch():
        async with get_db_session(tenant_id=tenant) as session:
            batch = [
                SpanRecord(
                    tenant_id=tenant,
                    trace_id=trace_id,
                    span_id=uuid.uuid4().hex[:16],
                    service_name="storage-load-svc",
                    name="persist_event",
                    kind="INTERNAL",
                    start_time_unix_nano=now,
                    end_time_unix_nano=now + 5_000,
                    duration_nanos=5_000,
                    status_code="OK",
                    attributes={"storage.load": True},
                    events=[],
                    links=[]
                )
                for _ in range(batch_size)
            ]
            session.add_all(batch)
            await session.flush()
        return True

    summary = await LoadTestingHarness.run_concurrent_query_load(
        query_fn=_write_batch,
        total_queries=4,  # 4 batches * 50 = 200 spans
        concurrency=2
    )

    assert summary.total_operations == 4
    assert summary.error_count == 0
    assert summary.duration_seconds > 0
    assert summary.p50_latency_ms > 0

    # Verify total spans in DB
    async with get_db_session(tenant_id=tenant) as session:
        stmt = select(func.count(SpanRecord.span_id)).where(SpanRecord.tenant_id == tenant)
        count = (await session.execute(stmt)).scalar()
        assert count == total_spans
