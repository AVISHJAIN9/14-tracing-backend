"""
Sampling Configuration API routes.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_tenant_id

router = APIRouter(prefix="/sampling", tags=["sampling"])

# In-memory tenant sampling rule registry
_TENANT_SAMPLING_RULES: Dict[str, List[Dict[str, Any]]] = {}

class SamplingRuleCreate(BaseModel):
    name: str = Field(..., min_length=1)
    service_pattern: Optional[str] = None
    route_pattern: Optional[str] = None
    sample_rate: float = Field(..., ge=0.0, le=1.0)

@router.get("/rules")
async def list_sampling_rules(tenant_id: str = Depends(get_tenant_id)) -> Dict[str, Any]:
    rules = _TENANT_SAMPLING_RULES.get(tenant_id, [])
    return {"tenant_id": tenant_id, "rules": rules, "count": len(rules)}

@router.post("/rules", status_code=201)
async def create_sampling_rule(
    payload: SamplingRuleCreate,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    rule_dict = {
        "name": payload.name,
        "service_pattern": payload.service_pattern,
        "route_pattern": payload.route_pattern,
        "sample_rate": payload.sample_rate
    }
    if tenant_id not in _TENANT_SAMPLING_RULES:
        _TENANT_SAMPLING_RULES[tenant_id] = []

    # Update if rule with same name exists, else append
    existing = next((r for r in _TENANT_SAMPLING_RULES[tenant_id] if r["name"] == payload.name), None)
    if existing:
        existing.update(rule_dict)
    else:
        _TENANT_SAMPLING_RULES[tenant_id].append(rule_dict)

    return rule_dict
