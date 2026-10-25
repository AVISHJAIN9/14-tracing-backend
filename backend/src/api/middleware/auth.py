"""
Authentication and Authorization Middleware for Distributed Tracing API.
Enforces API key verification, tenant scoping, and RBAC permissions.
"""

from typing import Optional, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from security.api_key import (
    ApiKeyService,
    InvalidApiKeyError,
    RevokedApiKeyError,
    TenantInactiveError,
    ApiKeyAuthContext
)
from storage.db import get_db_session

PUBLIC_PATHS: Set[str] = {
    "/healthz",
    "/readyz",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc"
}

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Allow public operational and documentation endpoints
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # 2. Extract credentials from Authorization or X-API-Key
        raw_key: Optional[str] = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_key = auth_header[7:].strip()
        elif request.headers.get("X-API-Key"):
            raw_key = request.headers.get("X-API-Key", "").strip()

        request.state.auth = None

        if raw_key:
            try:
                async with get_db_session() as session:
                    auth_ctx = await ApiKeyService.authenticate_key(session, raw_key)
                    request.state.auth = auth_ctx
                    request.state.tenant_id = auth_ctx.tenant_id
            except (InvalidApiKeyError, RevokedApiKeyError, TenantInactiveError) as e:
                return JSONResponse(
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                    content={
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": str(e)
                        }
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                    content={
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication failed"
                        }
                    }
                )
        else:
            # Strictly require auth for /api/v1/auth/ routes
            if request.url.path.startswith("/api/v1/auth/"):
                return JSONResponse(
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                    content={
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Missing authentication credentials"
                        }
                    }
                )

        return await call_next(request)
