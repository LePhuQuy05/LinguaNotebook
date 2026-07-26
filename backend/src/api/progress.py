"""Progress API — dashboard and report export."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.database import get_db
from src.core.dependencies import get_current_user_id
from src.models.sync import ProgressSnapshot
from src.models.learning import Lesson

router = APIRouter(prefix="/api/v1/progress", tags=["Progress"])


@router.get("/dashboard")
async def dashboard(
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard data: streaks, words, study time, daily snapshots, accuracy."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(ProgressSnapshot).where(
            ProgressSnapshot.user_id == user_id,
            ProgressSnapshot.date >= since,
        ).order_by(ProgressSnapshot.date)
    )
    snapshots = result.scalars().all()

    current_streak = snapshots[-1].streak_days if snapshots else 0
    total_words = sum(s.words_learned for s in snapshots)
    total_minutes = sum(s.study_minutes for s in snapshots)

    accuracy = {"vocabulary": 0, "reading": 0, "grammar": 0, "listening": 0}
    counts = {"vocabulary": 0, "reading": 0, "grammar": 0, "listening": 0}
    for s in snapshots:
        for key in accuracy:
            val = getattr(s, f"accuracy_{key}", None)
            if val is not None:
                accuracy[key] += val
                counts[key] += 1
    for key in accuracy:
        accuracy[key] = round(accuracy[key] / counts[key], 2) if counts[key] else None

    return {
        "current_streak": current_streak,
        "total_words_learned": total_words,
        "total_study_minutes": total_minutes,
        "daily_snapshots": [{"date": s.date.isoformat(), "words_learned": s.words_learned, "study_minutes": s.study_minutes, "streak_days": s.streak_days} for s in snapshots],
        "accuracy_by_type": accuracy,
    }


@router.post("/export-report")
async def export_report(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    user_id: str = Depends(get_current_user_id),
):
    """Export learning report (PDF generation placeholder)."""
    return {"report_url": f"/api/v1/progress/report/{user_id}/latest", "status": "generated"}
