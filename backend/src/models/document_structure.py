"""DocumentStructure ORM model — the curriculum map.

Rows are extracted from a textbook's table of contents (see
services/curriculum_service.py): part + chapter + topic + page range,
in reading order. Lessons walk this map instead of retrieving random
chunks.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentStructure(Base):
    __tablename__ = "document_structures"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    part: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    chapter_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chapter_title: Mapped[str] = mapped_column(String(500), nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
