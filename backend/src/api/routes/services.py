"""
Service and Operations API routes.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_tenant_id, get_db, require_permission
from security.rbac import Permission
from storage.models import SpanRecord

router = APIRouter(prefix="/services", tags=["services"])

@router.get("", dependencies=[Depends(require_permission(Permission.QUERY_SPANS))])
async def list_services(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = (
        select(SpanRecord.service_name)
        .where(SpanRecord.tenant_id == tenant_id)
        .distinct()
        .order_by(SpanRecord.service_name.asc())
    )
    result = await db.execute(stmt)
    services = [row[0] for row in result.all()]
    return {"services": services, "count": len(services)}

@router.get("/{service_name}/operations")
async def list_operations_for_service(
    service_name: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = (
        select(SpanRecord.name)
        .where(
            SpanRecord.tenant_id == tenant_id,
            SpanRecord.service_name == service_name
        )
        .distinct()
        .order_by(SpanRecord.name.asc())
    )
    result = await db.execute(stmt)
    operations = [row[0] for row in result.all()]
    return {
        "service_name": service_name,
        "operations": operations,
        "count": len(operations)
    }
