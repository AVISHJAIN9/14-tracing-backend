"""
Tenant-scoped trace ID management and multi-tenant trace identifier resolution.
Ensures trace IDs are scoped per tenant so identical trace IDs in separate tenants never collide.
"""

from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord, TraceRecord

@dataclass(frozen=True)
class TenantScopedTraceId:
    tenant_id: str
    trace_id: str

    def __post_init__(self):
        if not self.tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if not self.trace_id or len(self.trace_id) != 32:
            raise ValueError("trace_id must be a 32-character hex string")

    @property
    def composite_key(self) -> str:
        return f"{self.tenant_id}:{self.trace_id}"

class TenantScopedTraceStore:
    @staticmethod
    async def save_trace_header(
        session: AsyncSession,
        scoped_id: TenantScopedTraceId,
        root_service: str,
        root_name: str,
        start_nano: int,
        end_nano: int,
        duration_nano: int
    ) -> TraceRecord:
        record = TraceRecord(
            tenant_id=scoped_id.tenant_id,
            trace_id=scoped_id.trace_id,
            root_service_name=root_service,
            root_name=root_name,
            start_time_unix_nano=start_nano,
            end_time_unix_nano=end_nano,
            duration_nanos=duration_nano,
            span_count=1,
            error_count=0
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def get_trace_header(
        session: AsyncSession,
        scoped_id: TenantScopedTraceId
    ) -> Optional[TraceRecord]:
        stmt = select(TraceRecord).where(
            TraceRecord.tenant_id == scoped_id.tenant_id,
            TraceRecord.trace_id == scoped_id.trace_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
