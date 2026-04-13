"""
Application configuration settings.
Environment variables and constants.
"""
import os
import json
from typing import Optional, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields
    )

    # Application
    APP_NAME: str = "CRMSarvam"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    # Note: For Docker, this is overridden by docker-compose.yml
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/crmsarvam"

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Sarvam AI
    SARVAMAI_API_KEY: Optional[str] = None

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_AUDIO_EXTENSIONS: set = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    ALLOWED_VIDEO_EXTENSIONS: set = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    ALLOWED_DOCUMENT_EXTENSIONS: set = {".pdf", ".doc", ".docx", ".txt"}

    # Media Processing
    FFMPEG_PATH: str = "ffmpeg"  # Assumes ffmpeg is in PATH

    # CORS
    CORS_ORIGINS: Any = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS_ORIGINS from string or list."""
        # Handle None or empty values
        if v is None:
            return []

        # If already a list, return as-is
        if isinstance(v, list):
            return v

        # If string, parse it
        if isinstance(v, str):
            # Handle empty string
            if not v or v.strip() == "":
                return []

            # Try to parse as JSON array
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                # If JSON parsed but not a list, return empty
                return []
            except (json.JSONDecodeError, TypeError):
                pass

            # Fall back to comma-separated
            try:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            except (AttributeError, TypeError):
                return []

        # Return empty list for any other type
        return []

    @property
    def allowed_extensions(self) -> set:
        """All allowed file extensions."""
        return (
            self.ALLOWED_AUDIO_EXTENSIONS
            | self.ALLOWED_VIDEO_EXTENSIONS
            | self.ALLOWED_DOCUMENT_EXTENSIONS
        )


settings = Settings()
