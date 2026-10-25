"""
Streaming Span Ingestion Pipeline.
Handles continuous asynchronous streaming span ingestion from generators or network streams,
chunking incoming items and periodically flushing them into PostgreSQL.
"""

from typing import AsyncIterator, List
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord

class StreamingSpanIngester:
    def __init__(self, default_chunk_size: int = 50):
        self.default_chunk_size = default_chunk_size

    async def ingest_stream(
        self,
        session: AsyncSession,
        tenant_id: str,
        span_stream: AsyncIterator[SpanRecord],
        chunk_size: int | None = None
    ) -> AsyncIterator[int]:
        limit = chunk_size or self.default_chunk_size
        buffer: List[SpanRecord] = []

        async for span in span_stream:
            span.tenant_id = tenant_id
            buffer.append(span)

            if len(buffer) >= limit:
                session.add_all(buffer)
                await session.flush()
                flushed = len(buffer)
                buffer.clear()
                yield flushed

        # Flush any remaining items in buffer
        if buffer:
            session.add_all(buffer)
            await session.flush()
            flushed = len(buffer)
            buffer.clear()
            yield flushed
