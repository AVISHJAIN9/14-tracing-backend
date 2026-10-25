"""
Auth route handlers for inspecting current session credentials.
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/whoami")
async def whoami(request: Request) -> Dict[str, Any]:
    auth = getattr(request.state, "auth", None)
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Not authenticated"}}
        )
    return {
        "tenant_id": auth.tenant_id,
        "key_id": auth.key_id,
        "role": auth.role,
        "name": auth.name
    }
