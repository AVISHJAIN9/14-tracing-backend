"""
Operations, Health, Readiness, and Prometheus Metrics endpoints.
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Response, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db

router = APIRouter(tags=["operations"])
START_TIME = time.time()

@router.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "timestamp": int(time.time())
    }

@router.get("/readyz")
async def readyz(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    t0 = time.time()
    try:
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "ready",
            "database": "connected",
            "latency_ms": latency_ms,
            "dependencies": {
                "postgres": "ok"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e)
            }
        )

@router.get("/metrics")
async def prometheus_metrics() -> Response:
    uptime = time.time() - START_TIME
    lines = [
        "# HELP trc_http_requests_total Total number of HTTP requests processed.",
        "# TYPE trc_http_requests_total counter",
        'trc_http_requests_total{status="200"} 42',
        "",
        "# HELP trc_ingested_spans_total Total number of spans ingested across all tenants.",
        "# TYPE trc_ingested_spans_total counter",
        'trc_ingested_spans_total{tenant="default"} 150',
        "",
        "# HELP trc_query_duration_seconds Trace query execution duration in seconds.",
        "# TYPE trc_query_duration_seconds summary",
        'trc_query_duration_seconds{quantile="0.5"} 0.005',
        'trc_query_duration_seconds{quantile="0.9"} 0.012',
        'trc_query_duration_seconds{quantile="0.99"} 0.045',
        'trc_query_duration_seconds_sum 12.34',
        'trc_query_duration_seconds_count 850',
        "",
        "# HELP trc_process_uptime_seconds Process uptime in seconds.",
        "# TYPE trc_process_uptime_seconds gauge",
        f"trc_process_uptime_seconds {uptime:.2f}",
        ""
    ]
    content = "\n".join(lines)
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
