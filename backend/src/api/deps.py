"""
FastAPI Dependencies for Tenant resolution, DB session, Authentication, and RBAC authorization.
"""

from typing import AsyncGenerator, Optional, Callable
from fastapi import Header, HTTPException, Request, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from storage.db import get_db_session
from security.rbac import RbacService, Permission, Role, AccessDeniedError

async def get_tenant_id(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> str:
    auth = getattr(request.state, "auth", None)
    if auth:
        return auth.tenant_id
    if not x_tenant_id:
        return "default-tenant"
    clean = "".join(c for c in x_tenant_id if c.isalnum() or c in "-_")
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid tenant ID in header")
    return clean

async def get_db(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> AsyncGenerator[AsyncSession, None]:
    auth = getattr(request.state, "auth", None)
    tenant = auth.tenant_id if auth else (x_tenant_id or "default-tenant")
    async with get_db_session(tenant_id=tenant) as session:
        yield session

def require_permission(permission: Permission) -> Callable:
    """Dependency factory checking that caller has the given permission."""
    async def _perm_check(request: Request) -> None:
        auth = getattr(request.state, "auth", None)
        if auth:
            try:
                RbacService.enforce_permission([auth.role], permission)
            except AccessDeniedError as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": {"code": "FORBIDDEN", "message": str(e)}}
                )
    return _perm_check
