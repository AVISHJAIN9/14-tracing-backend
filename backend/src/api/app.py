"""
FastAPI application for Distributed Tracing Backend.
Exposes OpenTelemetry compatible REST APIs under /api/v1, /healthz, /readyz, /metrics.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy import select, func
from storage.db import init_db, get_db_session
from storage.models import Tenant, TraceRecord, SpanRecord
from api.routes.traces import router as traces_router
from api.routes.services import router as services_router
from api.routes.dependencies import router as dependencies_router
from api.routes.sampling import router as sampling_router
from api.routes.ingestion import router as ingestion_router
from api.routes.ops import router as ops_router
from api.routes.admin import router as admin_router
from api.routes.config import router as config_router
from api.routes.tenants import router as tenants_router
from api.routes.auth import router as auth_router
try:
    from api.routes.ml import router as ml_router
except Exception:
    ml_router = None
from api.middleware.auth import AuthenticationMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize schema
    await init_db()
    # Seed demo traces on cold start if table is empty
    try:
        async with get_db_session() as session:
            t_res = await session.execute(select(Tenant).where(Tenant.id == "default-tenant"))
            if not t_res.scalar_one_or_none():
                session.add(Tenant(id="default-tenant", name="Default Organization", status="active"))
                await session.commit()

            c_res = await session.execute(
                select(func.count(TraceRecord.trace_id)).where(TraceRecord.tenant_id == "default-tenant")
            )
            count = c_res.scalar() or 0
            if count == 0:
                now_ns = int(time.time() * 1e9)
                traces = [
                    ("trace-checkout-001", "api-gateway", "POST /checkout", 145_000_000, 4, 0),
                    ("trace-search-002", "api-gateway", "GET /search", 38_000_000, 2, 0),
                    ("trace-order-003", "order-service", "POST /orders", 412_000_000, 5, 1),
                    ("trace-user-004", "user-service", "GET /users/me", 19_000_000, 2, 0),
                    ("trace-notify-005", "worker-service", "POST /notifications", 85_000_000, 3, 0),
                ]
                for tid, svc, op, dur, sc, ec in traces:
                    session.add(TraceRecord(
                        tenant_id="default-tenant",
                        trace_id=tid,
                        root_service_name=svc,
                        root_name=op,
                        start_time_unix_nano=now_ns - 1_000_000_000,
                        end_time_unix_nano=now_ns - 1_000_000_000 + dur,
                        duration_nanos=dur,
                        span_count=sc,
                        error_count=ec
                    ))
                    session.add(SpanRecord(
                        tenant_id="default-tenant",
                        trace_id=tid,
                        span_id=tid.replace("trace-", "span-root-"),
                        parent_span_id=None,
                        name=op,
                        kind="SERVER",
                        start_time_unix_nano=now_ns - 1_000_000_000,
                        end_time_unix_nano=now_ns - 1_000_000_000 + dur,
                        duration_nanos=dur,
                        status_code="ERROR" if ec > 0 else "OK",
                        status_message="Downstream timeout" if ec > 0 else None,
                        service_name=svc,
                        attributes={"http.method": op.split()[0], "http.route": op.split()[1]},
                        events=[],
                        links=[]
                    ))
                await session.commit()
    except Exception as e:
        print(f"Warning: Demo seed skipped: {e}")
    yield

app = FastAPI(
    title="Distributed Tracing Backend API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
    elif isinstance(exc.detail, dict):
        content = {"error": exc.detail}
    else:
        content = {
            "error": {
                "code": "CLIENT_ERROR" if exc.status_code < 500 else "SERVER_ERROR",
                "message": str(exc.detail)
            }
        }
    return JSONResponse(status_code=exc.status_code, content=content)

# Authentication and Authorization middleware
app.add_middleware(AuthenticationMiddleware)

# Root operational endpoints
app.include_router(ops_router)

# Mount /api/v1 routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(traces_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(dependencies_router, prefix="/api/v1")
app.include_router(sampling_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
if ml_router:
    app.include_router(ml_router, prefix="/api/v1")

