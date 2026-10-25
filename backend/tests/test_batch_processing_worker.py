import uuid
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from collector.queue_buffer import RedisQueueBuffer
from collector.batch_worker import QueueBatchWorker
from storage.db import get_db_session
from security.tenant import TenantService

@pytest_asyncio.fixture
async def redis_client():
    client = aioredis.from_url("redis://localhost:6314/0", decode_responses=True)
    yield client
    await client.aclose()

@pytest.mark.asyncio
async def test_queue_batch_worker_drain_to_postgres(redis_client):
    stream_key = f"test:stream:{uuid.uuid4().hex[:8]}"
    group_name = "batch-worker-group"
    consumer_name = "worker-proc-1"

    buffer = RedisQueueBuffer(redis_client=redis_client, stream_key=stream_key)
    await buffer.setup_consumer_group(group_name=group_name)

    worker = QueueBatchWorker(buffer=buffer)

    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex

    # Push 3 batches with 5 spans each (15 spans total)
    for b in range(3):
        spans_batch = [
            {
                "trace_id": trace_id,
                "span_id": uuid.uuid4().hex[:16],
                "name": f"worker-op-{b}-{i}",
                "kind": "SERVER",
                "start_time_unix_nano": 1700000000000000000 + i * 1000,
                "end_time_unix_nano": 1700000000000000000 + (i + 1) * 1000,
                "duration_nanos": 1000,
                "status_code": "OK",
                "service_name": "worker-service",
                "attributes": {"batch.id": b, "item.id": i}
            }
            for i in range(5)
        ]
        await buffer.push_span_batch(tenant_id=tid, spans=spans_batch)

    # Execute worker processing cycle
    processed_count = await worker.process_one_cycle(
        group_name=group_name,
        consumer_name=consumer_name,
        batch_count=10,
        block_ms=500
    )
    assert processed_count == 15

    # Verify spans persisted in PostgreSQL 16
    async with get_db_session(tenant_id=tid) as session:
        stored = await TenantService.get_spans_for_tenant(session, tid, trace_id)
        assert len(stored) == 15
        assert all(s.service_name == "worker-service" for s in stored)

    # Cleanup
    await redis_client.delete(stream_key)
