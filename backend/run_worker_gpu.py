#!/usr/bin/env python3
"""
GPU Celery Worker - Run on HOST (not Docker) for Intel Arc GPU access.

Usage:
    python run_worker_gpu.py

Requirements (install once via setup_gpu.bat)

Per HPD-PARSING-GUIDE.md Section 2.2 Path B (Intel Arc XPU)
"""

import os
import sys

# Point to the backend source
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Override DATABASE_URL and REDIS_URL to connect to Docker services on localhost
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://linguanotebook:linguanotebook@localhost:5432/linguanotebook")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("GPU_ENABLED", "true")
os.environ.setdefault("GPU_TYPE", "xpu")
os.environ.setdefault("HPD_MODEL_PATH", os.path.join(os.path.dirname(__file__), "model"))
os.environ.setdefault("SECRET_KEY", "dev-secret-key-change-in-production")

if __name__ == "__main__":
    print("Starting LinguaNotebook Celery Worker with Intel XPU GPU...")
    print(f"  Database: {os.environ['DATABASE_URL']}")
    print(f"  Redis: {os.environ['REDIS_URL']}")
    print(f"  GPU Type: {os.environ['GPU_TYPE']}")
    print(f"  Model Path: {os.environ['HPD_MODEL_PATH']}")

    from src.workers.celery_app import celery_app

    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=1",
        "--pool=solo",  # Solo pool for GPU tasks (one process = one model load)
        "-Q", "parsing,embedding,lessons,celery",
    ])
