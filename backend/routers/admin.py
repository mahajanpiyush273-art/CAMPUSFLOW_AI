"""
CampusFlow AI - Admin Router
Handles administrative document management, AI recheck, review queue,
office administration, form submissions review, and system health checks.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends

from backend.llm import get_provider_health
from backend.security import require_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/health")
async def admin_health_check(user: Dict[str, Any] = Depends(require_role("admin"))):
    """Return AI model provider availability and active configurations without exposing keys."""
    health_info = get_provider_health()
    return health_info
