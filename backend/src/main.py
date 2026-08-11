"""LinguaNotebook — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import engine
from src.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    setup_logging()
    # Auto-create tables on startup (dev only — use Alembic for production)
    from src.core.database import Base
    from src.models.user import User  # noqa: F401
    from src.models.document import Document, ContentBlock  # noqa: F401
    from src.models.knowledge_segment import KnowledgeSegment  # noqa: F401
    from src.models.schedule import Schedule  # noqa: F401
    from src.models.learning import Lesson, LessonItem  # noqa: F401
    from src.models.srs import SRSCard  # noqa: F401
    from src.models.sync import Device, SyncLog, ProgressSnapshot  # noqa: F401
    from src.models.document_structure import DocumentStructure  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="LinguaNotebook API",
    version="1.0.0",
    description="Open-source language learning platform — REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from src.api import auth, documents, learning, rag, tts, sync, progress, donations

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(learning.router)
app.include_router(rag.router)
app.include_router(tts.router)
app.include_router(sync.router)
app.include_router(progress.router)
app.include_router(donations.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/v1/health/ready")
async def ready():
    from src.core.database import check_database
    from src.core.redis import check_redis
    from src.core.qdrant import check_qdrant

    return {
        "status": "ok",
        "postgres": await check_database(),
        "redis": await check_redis(),
        "qdrant": await check_qdrant(),
        "gpu_available": settings.gpu_enabled,
    }
