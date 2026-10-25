"""
Configuration API route handlers for distributed tracing backend.
Provides runtime inspection and dynamic tuning of tracing engine parameters.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/config", tags=["configuration"])

class SystemConfig(BaseModel):
    retention_days: int = Field(default=30, ge=1, le=3650, description="Data retention window in days")
    max_spans_per_trace: int = Field(default=10000, ge=10, le=1000000, description="Maximum spans per trace")
    default_sample_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Default head sampling ratio")
    ingestion_buffer_size: int = Field(default=10000, ge=100, le=1000000, description="In-memory ingestion queue size")
    rate_limit_per_second: int = Field(default=5000, ge=1, le=1000000, description="Rate limit per second per tenant")

class ConfigUpdate(BaseModel):
    retention_days: Optional[int] = Field(None, ge=1, le=3650)
    max_spans_per_trace: Optional[int] = Field(None, ge=10, le=1000000)
    default_sample_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    ingestion_buffer_size: Optional[int] = Field(None, ge=100, le=1000000)
    rate_limit_per_second: Optional[int] = Field(None, ge=1, le=1000000)

# Runtime dynamic configuration state
_current_config = SystemConfig()
_last_updated_ns = time.time_ns()

@router.get("", response_model=Dict[str, Any])
async def get_configuration() -> Dict[str, Any]:
    """Retrieve active system and engine configurations."""
    cfg = _current_config.model_dump()
    cfg["last_updated_ns"] = _last_updated_ns
    return cfg

@router.put("", response_model=Dict[str, Any])
async def update_configuration(update: ConfigUpdate) -> Dict[str, Any]:
    """Dynamically update system configuration settings."""
    global _last_updated_ns
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(_current_config, key, value)
    
    _last_updated_ns = time.time_ns()
    res = _current_config.model_dump()
    res["last_updated_ns"] = _last_updated_ns
    return res
