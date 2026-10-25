"""
Redis Streams Queue Buffering.
Durable bounded queue buffer connecting receiver endpoints with ingestion workers,
providing XADD batch buffering, consumer group registration, and reliable ACK processing.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
import redis.asyncio as aioredis
from redis.exceptions import ResponseError

class RedisQueueBuffer:
    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
        stream_key: str = "otlp:spans:stream",
        max_len: int = 100000
    ):
        self.client = redis_client or aioredis.from_url(
            "redis://localhost:6314/0", decode_responses=True
        )
        self.stream_key = stream_key
        self.max_len = max_len

    async def setup_consumer_group(self, group_name: str = "otlp:ingesters") -> None:
        try:
            await self.client.xgroup_create(
                name=self.stream_key,
                groupname=group_name,
                id="0",
                mkstream=True
            )
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def push_span_batch(
        self,
        tenant_id: str,
        spans: List[Dict[str, Any]],
        max_len: Optional[int] = None
    ) -> str:
        limit = max_len or self.max_len
        payload_str = json.dumps(spans)
        entry = {
            "tenant_id": tenant_id,
            "payload": payload_str,
        }
        msg_id = await self.client.xadd(
            name=self.stream_key,
            fields=entry,
            maxlen=limit,
            approximate=True
        )
        return str(msg_id)

    async def read_batch(
        self,
        group_name: str,
        consumer_name: str,
        count: int = 100,
        block_ms: int = 1000
    ) -> List[Tuple[str, str, List[Dict[str, Any]]]]:
        results = await self.client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={self.stream_key: ">"},
            count=count,
            block=block_ms
        )

        batches: List[Tuple[str, str, List[Dict[str, Any]]]] = []
        if not results:
            return batches

        for stream, entries in results:
            for entry_id, fields in entries:
                tenant_id = fields.get("tenant_id", "default-tenant")
                payload = json.loads(fields.get("payload", "[]"))
                batches.append((str(entry_id), tenant_id, payload))

        return batches

    async def ack(self, group_name: str, msg_id: str) -> int:
        res = await self.client.xack(self.stream_key, group_name, msg_id)
        return int(res)

    async def get_queue_len(self) -> int:
        return await self.client.xlen(self.stream_key)
