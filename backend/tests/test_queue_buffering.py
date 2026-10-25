import uuid
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from collector.queue_buffer import RedisQueueBuffer

@pytest_asyncio.fixture
async def redis_client():
    client = aioredis.from_url("redis://localhost:6314/0", decode_responses=True)
    yield client
    await client.aclose()

@pytest.mark.asyncio
async def test_redis_stream_queue_buffering(redis_client):
    stream_key = f"test:stream:{uuid.uuid4().hex[:8]}"
    group_name = "test-group"
    consumer_name = "worker-1"

    buffer = RedisQueueBuffer(redis_client=redis_client, stream_key=stream_key)
    await buffer.setup_consumer_group(group_name=group_name)

    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    spans_data = [
        {
            "trace_id": uuid.uuid4().hex,
            "span_id": uuid.uuid4().hex[:16],
            "name": "buffered-op",
            "service_name": "checkout",
            "duration_nanos": 500000
        }
        for _ in range(5)
    ]

    # 1. Push batch to Redis Stream
    msg_id = await buffer.push_span_batch(tenant_id=tid, spans=spans_data)
    assert msg_id is not None
    assert "-" in msg_id  # Redis stream ID format timestamp-seq

    # 2. Check stream depth
    depth = await buffer.get_queue_len()
    assert depth >= 1

    # 3. Read batch via consumer group
    messages = await buffer.read_batch(
        group_name=group_name,
        consumer_name=consumer_name,
        count=10,
        block_ms=500
    )
    assert len(messages) == 1
    read_id, read_tenant, read_spans = messages[0]
    assert read_id == msg_id
    assert read_tenant == tid
    assert len(read_spans) == 5
    assert read_spans[0]["name"] == "buffered-op"

    # 4. Acknowledge message
    ack_count = await buffer.ack(group_name=group_name, msg_id=msg_id)
    assert ack_count == 1

    # Cleanup
    await redis_client.delete(stream_key)
