"""
Tenant management and isolation service with application-level and DB-level boundaries.
"""

from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import Tenant, SpanRecord, TraceRecord

class TenantNotFoundError(Exception):
    pass

class TenantInactiveError(Exception):
    pass

class CrossTenantAccessError(Exception):
    pass

@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    name: str
    status: str

class TenantService:
    @staticmethod
    async def create_tenant(session: AsyncSession, tenant_id: str, name: str) -> Tenant:
        clean_id = "".join(c for c in tenant_id if c.isalnum() or c in "-_")
        if not clean_id:
            raise ValueError("Invalid tenant ID")
        tenant = Tenant(id=clean_id, name=name, status="active")
        session.add(tenant)
        await session.flush()
        return tenant

    @staticmethod
    async def get_tenant(session: AsyncSession, tenant_id: str) -> Tenant:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise TenantNotFoundError(f"Tenant '{tenant_id}' not found")
        if tenant.status != "active":
            raise TenantInactiveError(f"Tenant '{tenant_id}' is not active")
        return tenant

    @staticmethod
    async def get_spans_for_tenant(
        session: AsyncSession,
        caller_tenant_id: str,
        target_trace_id: str
    ) -> List[SpanRecord]:
        """
        Fetch spans for a trace while enforcing strict tenant boundaries.
        Both application filter and PostgreSQL RLS ensure zero cross-tenant leakage.
        """
        # App-level enforcement
        stmt = select(SpanRecord).where(
            SpanRecord.tenant_id == caller_tenant_id,
            SpanRecord.trace_id == target_trace_id
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
