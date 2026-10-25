"""
Idempotent Span Ingestion.
Ensures duplicate delivery of the exact same span batch is idempotent
using PostgreSQL ON CONFLICT DO NOTHING semantics on (tenant_id, trace_id, span_id).
Prevents duplicate rows and ensures retry safety.
"""

from typing import List
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord

class IdempotentSpanIngester:
    async def ingest_spans_idempotent(
        self,
        session: AsyncSession,
        tenant_id: str,
        spans: List[SpanRecord]
    ) -> int:
        if not spans:
            return 0

        values = []
        for s in spans:
            values.append({
                "tenant_id": tenant_id,
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "name": s.name,
                "kind": s.kind,
                "start_time_unix_nano": s.start_time_unix_nano,
                "end_time_unix_nano": s.end_time_unix_nano,
                "duration_nanos": s.duration_nanos,
                "status_code": s.status_code,
                "status_message": s.status_message,
                "attributes": s.attributes,
                "events": s.events,
                "links": s.links,
                "service_name": s.service_name,
            })

        stmt = pg_insert(SpanRecord).values(values).on_conflict_do_nothing(
            index_elements=["tenant_id", "trace_id", "span_id"]
        )

        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount if result.rowcount is not None else len(values)
