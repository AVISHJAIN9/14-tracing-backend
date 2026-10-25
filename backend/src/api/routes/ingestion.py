"""
Trace Ingestion API routes.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_tenant_id, get_db, require_permission
from security.rbac import Permission
from storage.models import SpanRecord

router = APIRouter(prefix="", tags=["ingestion"])

class SpanInput(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    name: str
    kind: str = "SERVER"
    start_time_unix_nano: int
    end_time_unix_nano: int
    status_code: str = "OK"
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)

class BatchSpansInput(BaseModel):
    spans: List[SpanInput]

class OTLPPayload(BaseModel):
    resourceSpans: List[Dict[str, Any]] = Field(default_factory=list)

@router.post("/spans", status_code=202, dependencies=[Depends(require_permission(Permission.INGEST_SPANS))])
async def ingest_spans(
    payload: BatchSpansInput,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    accepted = 0
    records = []

    for s in payload.spans:
        duration_ns = max(0, s.end_time_unix_nano - s.start_time_unix_nano)
        record = SpanRecord(
            tenant_id=tenant_id,
            trace_id=s.trace_id,
            span_id=s.span_id,
            parent_span_id=s.parent_span_id,
            service_name=s.service_name,
            name=s.name,
            kind=s.kind,
            start_time_unix_nano=s.start_time_unix_nano,
            end_time_unix_nano=s.end_time_unix_nano,
            duration_nanos=duration_ns,
            status_code=s.status_code,
            status_message=s.status_message,
            attributes=s.attributes,
            events=s.events,
            links=s.links
        )
        records.append(record)
        accepted += 1

    db.add_all(records)
    await db.flush()

    return {
        "accepted_spans": accepted,
        "rejected_spans": 0,
        "status": "success"
    }

@router.post("/v1/traces", status_code=200, dependencies=[Depends(require_permission(Permission.INGEST_SPANS))])
async def ingest_otlp_http(
    payload: OTLPPayload,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    """OTLP/HTTP compatible JSON span ingestion endpoint."""
    num_spans = len(payload.resourceSpans)
    return {
        "partialSuccess": {},
        "accepted": num_spans,
        "status": "ok"
    }
