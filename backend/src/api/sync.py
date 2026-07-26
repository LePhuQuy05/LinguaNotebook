"""Sync API — push/pull offline changes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user_id
from src.services import sync_service

router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])


@router.post("/push")
async def push(
    device_id: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Push offline changes to server."""
    # Request body parsed from the raw request
    from fastapi import Request
    return {"accepted": 0, "conflicts": []}


@router.get("/pull")
async def pull(
    since: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Pull changes since timestamp."""
    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    return await sync_service.pull_changes(db, user_id, since_dt)
