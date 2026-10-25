"""
Admin API route handlers for distributed tracing backend.
Provides cluster maintenance, span statistics, and data purge operations.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_tenant_id, require_permission
from security.rbac import Permission
from storage.models import SpanRecord, TraceRecord

router = APIRouter(prefix="/admin", tags=["admin"])

class PurgeRequest(BaseModel):
    older_than_ns: int = Field(..., gt=0, description="Cutoff timestamp in nanoseconds")

@router.get("/stats")
async def get_admin_stats(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve operational and storage statistics for the tenant."""
    query_spans = select(func.count()).select_from(SpanRecord).where(SpanRecord.tenant_id == tenant_id)
    query_traces = select(func.count()).select_from(TraceRecord).where(TraceRecord.tenant_id == tenant_id)

    total_spans = await session.scalar(query_spans) or 0
    total_traces = await session.scalar(query_traces) or 0

    # Estimate bytes dynamically based on span count
    est_bytes = total_spans * 1024
    curr_time_ns = time.time_ns()

    return {
        "tenant_id": tenant_id,
        "total_spans": int(total_spans),
        "total_traces": int(total_traces),
        "storage": {
            "estimated_bytes": int(est_bytes),
            "engine": "postgresql"
        },
        "sampled_at_ns": curr_time_ns
    }

@router.post("/purge", dependencies=[Depends(require_permission(Permission.DELETE_SPANS))])
async def purge_old_data(
    req: PurgeRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Purge spans and traces older than the specified nanosecond timestamp."""
    stmt_spans = delete(SpanRecord).where(
        SpanRecord.tenant_id == tenant_id,
        SpanRecord.start_time_unix_nano < req.older_than_ns
    )
    res_spans = await session.execute(stmt_spans)
    purged_spans_count = res_spans.rowcount or 0

    stmt_traces = delete(TraceRecord).where(
        TraceRecord.tenant_id == tenant_id,
        TraceRecord.start_time_unix_nano < req.older_than_ns
    )
    res_traces = await session.execute(stmt_traces)
    purged_traces_count = res_traces.rowcount or 0

    await session.commit()
    t_done = time.time_ns()

    return {
        "tenant_id": tenant_id,
        "purged_spans": int(purged_spans_count),
        "purged_traces": int(purged_traces_count),
        "cutoff_ns": req.older_than_ns,
        "completed_at_ns": t_done
    }
