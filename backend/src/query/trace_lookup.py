"""
Trace Lookup Query Engine.
Provides high-performance trace retrieval by trace ID, assembling spans into
hierarchical trace trees, calculating total duration, service dependencies, and error status.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord

@dataclass
class TraceDetailView:
    trace_id: str
    root_span_id: Optional[str]
    total_spans: int
    duration_nanos: int
    has_errors: bool
    services: Set[str]
    spans: List[Dict[str, Any]]

class TraceLookupService:
    @staticmethod
    def _validate_trace_id(trace_id: str) -> str:
        if not trace_id or len(trace_id) != 32:
            raise ValueError(f"Invalid trace_id: must be 32 hex characters, got {trace_id}")
        try:
            int(trace_id, 16)
        except ValueError:
            raise ValueError(f"Invalid trace_id hex format: {trace_id}")
        if trace_id == "0" * 32:
            raise ValueError("All-zero trace_id is invalid")
        return trace_id.lower()

    async def get_trace_by_id(
        self,
        session: AsyncSession,
        tenant_id: str,
        trace_id: str
    ) -> Optional[TraceDetailView]:
        valid_trace_id = self._validate_trace_id(trace_id)

        stmt = (
            select(SpanRecord)
            .where(
                SpanRecord.tenant_id == tenant_id,
                SpanRecord.trace_id == valid_trace_id
            )
            .order_by(SpanRecord.start_time_unix_nano.asc())
        )
        result = await session.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return None

        # Build span dictionary and identify root span
        all_span_ids = {r.span_id for r in records}
        root_span_id: Optional[str] = None
        has_errors = False
        services: Set[str] = set()

        min_start = records[0].start_time_unix_nano
        max_end = records[0].end_time_unix_nano

        spans_list: List[Dict[str, Any]] = []
        for r in records:
            services.add(r.service_name)
            if r.status_code == "ERROR":
                has_errors = True

            if r.start_time_unix_nano < min_start:
                min_start = r.start_time_unix_nano
            if r.end_time_unix_nano > max_end:
                max_end = r.end_time_unix_nano

            if r.parent_span_id is None or r.parent_span_id not in all_span_ids:
                if root_span_id is None:
                    root_span_id = r.span_id

            spans_list.append({
                "tenant_id": r.tenant_id,
                "trace_id": r.trace_id,
                "span_id": r.span_id,
                "parent_span_id": r.parent_span_id,
                "name": r.name,
                "kind": r.kind,
                "start_time_unix_nano": r.start_time_unix_nano,
                "end_time_unix_nano": r.end_time_unix_nano,
                "duration_nanos": r.duration_nanos,
                "status_code": r.status_code,
                "status_message": r.status_message,
                "attributes": r.attributes,
                "events": r.events,
                "links": r.links,
                "service_name": r.service_name,
            })

        duration_nanos = max(0, max_end - min_start)

        return TraceDetailView(
            trace_id=valid_trace_id,
            root_span_id=root_span_id,
            total_spans=len(records),
            duration_nanos=duration_nanos,
            has_errors=has_errors,
            services=services,
            spans=spans_list
        )
