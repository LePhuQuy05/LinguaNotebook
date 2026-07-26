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
