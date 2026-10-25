"""
Tenant API route handlers for distributed tracing backend.
Manages multi-tenant registration, metadata, quotas, and lifecycle states.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from storage.models import Tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])

class TenantCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, description="Unique tenant identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Tenant legal or display name")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Custom tenant quota and routing configurations")

class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="Status: active, suspended, or archived")
    settings: Optional[Dict[str, Any]] = None

class TenantResponse(BaseModel):
    id: str
    name: str
    status: str
    settings: Dict[str, Any]
    created_at: str

@router.post("", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(
    req: TenantCreate,
    session: AsyncSession = Depends(get_db)
) -> TenantResponse:
    """Register a new tenant in the system."""
    existing = await session.get(Tenant, req.id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tenant {req.id} already exists")

    tenant = Tenant(
        id=req.id,
        name=req.name,
        status="active",
        settings=req.settings
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        status=tenant.status,
        settings=tenant.settings or {},
        created_at=tenant.created_at.isoformat()
    )

@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    session: AsyncSession = Depends(get_db)
) -> List[TenantResponse]:
    """List all registered tenants."""
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    res = await session.execute(stmt)
    tenants = res.scalars().all()
    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            status=t.status,
            settings=t.settings or {},
            created_at=t.created_at.isoformat()
        )
        for t in tenants
    ]

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_db)
) -> TenantResponse:
    """Retrieve details for a specific tenant."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found")
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        status=tenant.status,
        settings=tenant.settings or {},
        created_at=tenant.created_at.isoformat()
    )

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    session: AsyncSession = Depends(get_db)
) -> TenantResponse:
    """Update tenant configuration or status."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found")

    if update.name is not None:
        tenant.name = update.name
    if update.status is not None:
        tenant.status = update.status
    if update.settings is not None:
        tenant.settings = update.settings

    await session.commit()
    await session.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        status=tenant.status,
        settings=tenant.settings or {},
        created_at=tenant.created_at.isoformat()
    )
