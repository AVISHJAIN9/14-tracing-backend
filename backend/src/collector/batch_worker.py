"""
Queue Batch Ingestion Worker.
Consumes batches of spans from Redis Streams queue buffer, converts them
to normalized database records, bulk-persists them into PostgreSQL, and ACKs
messages upon successful transaction commit.
"""

from typing import List, Optional
from collector.queue_buffer import RedisQueueBuffer
from collector.otlp import OtlpIngestService
from storage.db import get_db_session
from storage.models import SpanRecord

class QueueBatchWorker:
    def __init__(
        self,
        buffer: RedisQueueBuffer,
        ingest_service: Optional[OtlpIngestService] = None,
    ):
        self.buffer = buffer
        self.ingest_service = ingest_service or OtlpIngestService()

    async def process_one_cycle(
        self,
        group_name: str,
        consumer_name: str,
        batch_count: int = 50,
        block_ms: int = 500
    ) -> int:
        messages = await self.buffer.read_batch(
            group_name=group_name,
            consumer_name=consumer_name,
            count=batch_count,
            block_ms=block_ms
        )

        total_processed = 0

        for msg_id, tenant_id, spans_data in messages:
            records: List[SpanRecord] = []
            for item in spans_data:
                rec = SpanRecord(
                    tenant_id=tenant_id,
                    trace_id=item["trace_id"],
                    span_id=item["span_id"],
                    parent_span_id=item.get("parent_span_id"),
                    name=item.get("name", "op"),
                    kind=item.get("kind", "INTERNAL"),
                    start_time_unix_nano=item.get("start_time_unix_nano", 0),
                    end_time_unix_nano=item.get("end_time_unix_nano", 0),
                    duration_nanos=item.get("duration_nanos", 0),
                    status_code=item.get("status_code", "UNSET"),
                    status_message=item.get("status_message"),
                    attributes=item.get("attributes", {}),
                    events=item.get("events", []),
                    links=item.get("links", []),
                    service_name=item.get("service_name", "unknown")
                )
                records.append(rec)

            async with get_db_session(tenant_id=tenant_id) as session:
                await self.ingest_service.batch_ingest_records(session, tenant_id, records)

            await self.buffer.ack(group_name=group_name, msg_id=msg_id)
            total_processed += len(records)

        return total_processed
