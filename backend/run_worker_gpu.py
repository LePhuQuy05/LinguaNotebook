#!/usr/bin/env python3
"""
GPU Celery Worker — Run on HOST (not Docker) for Intel Arc GPU access.

Usage:
    C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe run_worker_gpu.py

Requirements (install once):
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu
    pip install "transformers>=4.46,<5" accelerate einops timm sentencepiece safetensors
    pip install celery redis sqlalchemy pydantic pydantic-settings pymupdf pillow
    pip install python-jose passlib bcrypt==4.0.1 structlog boto3 httpx

Per HPD-PARSING-GUIDE.md Section 2.2 Path B (Intel Arc XPU)
"""

import os
import sys

# Point to the backend source
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Override DATABASE_URL and REDIS_URL to connect to Docker services on localhost
os.environ.setdefault("DATABASE_URL", "postgresql://linguanotebook:linguanotebook@localhost:5432/linguanotebook")
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
