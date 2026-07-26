"""SRS service — SM-2 spaced repetition algorithm."""

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.srs import SRSCard

logger = logging.getLogger(__name__)
MIN_EF = 1.3
LEECH_THRESHOLD = 5


async def create_card(db: AsyncSession, user_id: str, front: str, back: str, segment_id: str | None = None) -> SRSCard:
    card = SRSCard(user_id=user_id, knowledge_segment_id=segment_id, front=front, back=back, next_review_date=date.today() + timedelta(days=1))
    db.add(card)
    await db.commit()
    return card


async def get_due_cards(db: AsyncSession, user_id: str, limit: int = 10) -> list[SRSCard]:
    result = await db.execute(
        select(SRSCard).where(SRSCard.user_id == user_id, SRSCard.next_review_date <= date.today(), SRSCard.is_suspended == False).order_by(SRSCard.next_review_date).limit(limit)
    )
    return list(result.scalars().all())


async def rate_card(db: AsyncSession, card_id: str, score: int) -> SRSCard | None:
    result = await db.execute(select(SRSCard).where(SRSCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        return None

    ef = card.ease_factor
    if score >= 3:
        if card.repetitions == 0:
            card.interval_days = 1
        elif card.repetitions == 1:
            card.interval_days = 6
        else:
            card.interval_days = round(card.interval_days * ef)
        card.repetitions += 1
        card.consecutive_failures = 0
    else:
        card.interval_days = 1
        card.repetitions = 0
        card.consecutive_failures += 1

    # EF adjustments
    ef_deltas = {5: 0.1, 4: 0.0, 3: -0.14, 2: -0.22, 1: -0.30}
    ef += ef_deltas.get(score, 0)
    card.ease_factor = max(MIN_EF, ef)

    # Leech detection
    if card.consecutive_failures >= LEECH_THRESHOLD:
        card.is_suspended = True

    card.last_score = score
    card.last_review_date = date.today()
    card.next_review_date = date.today() + timedelta(days=max(1, int(card.interval_days)))
    await db.commit()
    return card
