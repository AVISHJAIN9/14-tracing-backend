"""
Trace and Search API routes.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_tenant_id, get_db
from query.trace_lookup import TraceLookupService
from query.trace_search import TraceSearchService

from query.critical_path import CriticalPathAnalyzer

router = APIRouter(prefix="/traces", tags=["traces"])
lookup_service = TraceLookupService()
search_service = TraceSearchService()

@router.get("/{trace_id}/critical-path")
async def get_trace_critical_path(
    trace_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        trace = await lookup_service.get_trace_by_id(session=db, tenant_id=tenant_id, trace_id=trace_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")

    result = CriticalPathAnalyzer.compute_critical_path(trace.spans)
    return {
        "trace_id": trace_id,
        **result
    }


@router.get("")
@router.get("/search")
async def search_traces(
    service_name: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    operation_name: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    status_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_duration_ns: Optional[int] = Query(None),
    min_duration_ms: Optional[float] = Query(None),
    max_duration_ns: Optional[int] = Query(None),
    max_duration_ms: Optional[float] = Query(None),
    query_text: Optional[str] = Query(None),
    order_by: str = Query("start_time"),
    order_dir: str = Query("desc"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    effective_service = service_name or service
    effective_op = operation_name or operation
    effective_status = status_code or status
    effective_min_ns = min_duration_ns if min_duration_ns is not None else (int(min_duration_ms * 1_000_000) if min_duration_ms is not None else None)
    effective_max_ns = max_duration_ns if max_duration_ns is not None else (int(max_duration_ms * 1_000_000) if max_duration_ms is not None else None)

    results = await search_service.search_traces(
        session=db,
        tenant_id=tenant_id,
        service_name=effective_service,
        operation_name=effective_op,
        status_code=effective_status,
        min_duration_ns=effective_min_ns,
        max_duration_ns=effective_max_ns,
        query_text=query_text,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset
    )

    items = [
        {
            "trace_id": r.trace_id,
            "root_name": r.root_name,
            "root_service": r.root_service,
            "root_service_name": r.root_service,
            "start_time_unix_nano": r.start_time_unix_nano,
            "duration_nanos": r.duration_nanos,
            "span_count": r.span_count,
            "error_count": 1 if r.has_errors else 0,
            "has_errors": r.has_errors
        }
        for r in results
    ]

    return {
        "results": items,
        "traces": items,
        "count": len(items),
        "total_matches": len(items),
        "limit": limit,
        "offset": offset
    }

@router.get("/{trace_id}")
async def get_trace_by_id(
    trace_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        trace = await lookup_service.get_trace_by_id(session=db, tenant_id=tenant_id, trace_id=trace_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")

    root_svc = list(trace.services)[0] if trace.services else "unknown"
    return {
        "trace_id": trace.trace_id,
        "root_span_id": trace.root_span_id,
        "total_spans": trace.total_spans,
        "span_count": trace.total_spans,
        "duration_nanos": trace.duration_nanos,
        "has_errors": trace.has_errors,
        "error_count": 1 if trace.has_errors else 0,
        "root_service": root_svc,
        "services": list(trace.services),
        "spans": trace.spans
    }
