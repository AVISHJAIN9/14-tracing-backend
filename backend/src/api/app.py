"""
FastAPI application for Distributed Tracing Backend.
Exposes OpenTelemetry compatible REST APIs under /api/v1, /healthz, /readyz, /metrics.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
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

app = FastAPI(
    title="Distributed Tracing Backend API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
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

