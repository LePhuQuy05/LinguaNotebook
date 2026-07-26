"""Document and ContentBlock ORM models."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class DocumentStatus(str, enum.Enum):
    uploading = "uploading"
    queued = "queued"
    parsing = "parsing"
    completed = "completed"
    completed_with_errors = "completed_with_errors"
    failed = "failed"


class BlockType(str, enum.Enum):
    header = "header"
    paragraph = "paragraph"
    table = "table"
    list = "list"
    image_caption = "image_caption"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.uploading
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_content_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    blocks: Mapped[list["ContentBlock"]] = relationship(
        "ContentBlock", back_populates="document", cascade="all, delete-orphan"
    )


class ContentBlock(Base):
    __tablename__ = "content_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[BlockType] = mapped_column(Enum(BlockType), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    difficulty_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="intermediate"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document: Mapped["Document"] = relationship("Document", back_populates="blocks")
