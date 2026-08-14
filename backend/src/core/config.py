"""Application configuration via Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration from environment variables with sensible defaults."""

    # General
    secret_key: str = "change-me"
    environment: str = "development"
    self_hosted: bool = False
    log_level: str = "INFO"
    gpu_enabled: bool = False
    gpu_type: str = "xpu"  # "cuda" for NVIDIA, "xpu" for Intel Arc

    # PostgreSQL
    database_url: str = (
        "postgresql+asyncpg://linguanotebook:linguanotebook@localhost:5432/linguanotebook"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # S3 / MinIO Storage
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "linguanotebook"
    storage_use_ssl: bool = False

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # OAuth (optional)
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # HPD Model
    hpd_model_path: str = "./model"

    # Optional SLM for curriculum escalation (feature 008, ticket 03):
    # a directory containing a .gguf, or the path to a .gguf file. Empty /
    # unresolvable → escalation is disabled and extraction degrades to the
    # rule scan only (same behaviour as before the feature existed).
    curriculum_llm_path: str = "./model/curriculum-llm"

    # OCR backend for image-based PDFs:
    #   "auto"   → PaddleOCR-VL cloud API if a token is configured, else local HPD
    #   "paddle" → cloud API only (requires PADDLE_OCR_TOKEN)
    #   "local"  → local HPD GPU model only
    ocr_backend: str = "auto"

    # PaddleOCR-VL cloud API (https://ai.baidu.com/ai-doc/AISTUDIO/7mfz6dgx9)
    paddle_ocr_token: str = ""  # bearer token — keep in .env, never commit
    paddle_ocr_job_url: str = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    paddle_ocr_model: str = "PaddleOCR-VL-1.6"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:19006"]

    # Donations
    github_sponsors_url: str = ""
    kofi_url: str = ""

    # Monitoring
    sentry_dsn: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
