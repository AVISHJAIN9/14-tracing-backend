import uuid
import asyncio
import pytest
from sqlalchemy import select, func
from collector.stream_ingest import StreamingSpanIngester
from storage.db import get_db_session
from storage.models import SpanRecord
from security.tenant import TenantService

async def async_span_stream(tenant_id: str, trace_id: str, count: int):
    for i in range(count):
        yield SpanRecord(
            tenant_id=tenant_id,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=None,
            name=f"stream-op-{i}",
            kind="INTERNAL",
            start_time_unix_nano=1700000000000000000 + i * 100000,
            end_time_unix_nano=1700000000000000000 + (i + 1) * 100000,
            duration_nanos=100000,
            status_code="OK",
            status_message=None,
            attributes={"stream.seq": i},
            events=[],
            links=[],
            service_name="streaming-service"
        )
        if i % 10 == 0:
            await asyncio.sleep(0.01)

@pytest.mark.asyncio
async def test_streaming_span_ingestion_pipeline():
    ingester = StreamingSpanIngester()
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex

    stream = async_span_stream(tid, trace_id, count=35)
    chunk_flushes = []

    async with get_db_session(tenant_id=tid) as session:
        async for flushed_count in ingester.ingest_stream(session, tid, stream, chunk_size=10):
            chunk_flushes.append(flushed_count)

    # With count=35 and chunk_size=10, we expect chunks of 10, 10, 10, 5
    assert len(chunk_flushes) == 4
    assert sum(chunk_flushes) == 35

    # Verify spans persisted in PostgreSQL 16
    async with get_db_session(tenant_id=tid) as session:
        spans = await TenantService.get_spans_for_tenant(session, tid, trace_id)
        assert len(spans) == 35
        assert all(s.service_name == "streaming-service" for s in spans)
