"""
Service Dependency Graph API.
Computes caller/callee relationships from parent-child span links.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_tenant_id, get_db
from storage.models import SpanRecord

router = APIRouter(prefix="/dependencies", tags=["dependencies"])

@router.get("")
async def get_service_dependencies(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    parent_span = aliased(SpanRecord)
    child_span = aliased(SpanRecord)

    stmt = (
        select(
            parent_span.service_name.label("parent"),
            child_span.service_name.label("child"),
            func.count().label("call_count"),
            func.count().filter(child_span.status_code == "ERROR").label("error_count")
        )
        .join(
            child_span,
            and_(
                child_span.tenant_id == parent_span.tenant_id,
                child_span.trace_id == parent_span.trace_id,
                child_span.parent_span_id == parent_span.span_id,
                child_span.service_name != parent_span.service_name
            )
        )
        .where(parent_span.tenant_id == tenant_id)
        .group_by(parent_span.service_name, child_span.service_name)
        .order_by(parent_span.service_name.asc(), child_span.service_name.asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    dependencies = [
        {
            "parent": row.parent,
            "child": row.child,
            "caller": row.parent,
            "callee": row.child,
            "call_count": int(row.call_count),
            "error_count": int(row.error_count or 0)
        }
        for row in rows
    ]

    return {"dependencies": dependencies, "count": len(dependencies)}
