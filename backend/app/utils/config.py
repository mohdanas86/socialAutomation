"""
Configuration management using Pydantic Settings.

WHY THIS FILE EXISTS:
- Centralized environment variable loading
- Type-safe configuration with defaults
- Easy to validate required variables
- Can override for testing

WHAT IT DOES:
- Loads .env file automatically
- Validates that required vars are set
- Provides clean access to config throughout app
- Separates config from code
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB
    mongodb_url: str
    mongodb_db_name: str = "social_automation"

    # FastAPI
    app_env: str = "development"
    app_name: str = "Social Media Automation"
    debug: bool = True
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # LinkedIn OAuth
    linkedin_client_id: str
    linkedin_client_secret: str
    linkedin_redirect_uri: str
    linkedin_api_version: str = "v2"
    linkedin_base_url: str = "https://api.linkedin.com"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]

    # Retry Configuration
    max_retries: int = 3
    retry_backoff_base: int = 5  # Exponential backoff base

    # Gemini
    gemini_api_key: str = ""

    class Config:
        # Automatically load from .env file
        env_file = ".env"
        case_sensitive = False  # APP_ENV or app_env both work


# Create single instance to import everywhere
settings = Settings()


def validate_settings() -> None:
    """
    Validate that all required settings are present.
    Call this on app startup to fail fast if config is wrong.
    """
    required_fields = [
        "mongodb_url",
        "linkedin_client_id",
        "linkedin_client_secret",
        "linkedin_redirect_uri",
        "jwt_secret_key",
    ]

    missing = [field for field in required_fields if not getattr(settings, field)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
