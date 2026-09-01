import os
from pathlib import Path
from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend/.env absolutely if present, so uvicorn cwd does not matter
_env_path = Path(__file__).resolve().parents[2] / ".env"
_BACKEND_ENV = str(_env_path) if _env_path.exists() else None

class Settings(BaseSettings):
    # Application Environment: development | production | test
    APP_ENV: str = "development"
    ENV: Optional[str] = None  # legacy alias

    # Database
    DATABASE_URL: str = "sqlite:///./finsense.db"

    # Security & Auth
    JWT_SECRET_KEY: str = "dev-secret-change-in-prod-please-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # URLs & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    CORS_ORIGINS: Optional[str] = None  # legacy alias

    # AI / ML
    AI_PROVIDER: str = "openai"
    AI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Email provider: smtp | resend | auto
    EMAIL_PROVIDER: str = "smtp"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "FinSense <noreply@finsense.app>"

    # SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_USER: Optional[str] = None  # alias
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM: Optional[str] = None  # alias
    SMTP_USE_TLS: bool = True
    SMTP_TLS: Optional[bool] = None  # alias

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV,
        extra="allow",
        case_sensitive=False
    )

    @model_validator(mode="after")
    def harmonize_and_validate(self):
        # Harmonize legacy aliases
        if self.ENV and not os.getenv("APP_ENV"):
            self.APP_ENV = self.ENV

        if self.CORS_ORIGINS and not os.getenv("ALLOWED_ORIGINS"):
            self.ALLOWED_ORIGINS = self.CORS_ORIGINS

        if self.SMTP_USER and not self.SMTP_USERNAME:
            self.SMTP_USERNAME = self.SMTP_USER
        elif self.SMTP_USERNAME and not self.SMTP_USER:
            self.SMTP_USER = self.SMTP_USERNAME

        if self.SMTP_FROM and not self.SMTP_FROM_EMAIL:
            self.SMTP_FROM_EMAIL = self.SMTP_FROM
        elif self.SMTP_FROM_EMAIL and not self.SMTP_FROM:
            self.SMTP_FROM = self.SMTP_FROM_EMAIL

        if self.SMTP_TLS is not None and os.getenv("SMTP_USE_TLS") is None:
            self.SMTP_USE_TLS = self.SMTP_TLS
        elif self.SMTP_USE_TLS is not None and self.SMTP_TLS is None:
            self.SMTP_TLS = self.SMTP_USE_TLS

        # Production Validation Guard
        is_production = self.APP_ENV.lower() in ("production", "prod")
        if is_production:
            errors = []

            # 1. DATABASE_URL validation
            if not self.DATABASE_URL or self.DATABASE_URL.startswith("sqlite"):
                errors.append("DATABASE_URL must be a valid PostgreSQL connection string in production (SQLite is not permitted).")

            # 2. JWT_SECRET_KEY validation
            weak_keys = {
                "dev-secret-change-in-prod-please-32chars",
                "change-me",
                "change-me-32chars-min",
                "secret",
                "secret123",
            }
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY in weak_keys or len(self.JWT_SECRET_KEY) < 32:
                errors.append("JWT_SECRET_KEY must be set to a secure, random secret of at least 32 characters in production.")

            # 3. FRONTEND_URL validation
            if not self.FRONTEND_URL or "localhost" in self.FRONTEND_URL or "127.0.0.1" in self.FRONTEND_URL:
                errors.append("FRONTEND_URL must be configured with your production frontend domain (e.g., https://your-domain.vercel.app).")

            if errors:
                raise ValueError(
                    "[CONFIG ERROR] Production configuration validation failed:\n  - "
                    + "\n  - ".join(errors)
                )

        return self

    @property
    def cors_origins_list(self) -> List[str]:
        origins = set()
        raw = self.ALLOWED_ORIGINS or self.CORS_ORIGINS or ""
        for o in raw.split(","):
            cleaned = o.strip().rstrip("/")
            if cleaned:
                origins.add(cleaned)
        # Ensure FRONTEND_URL is in CORS origins
        if self.FRONTEND_URL:
            origins.add(self.FRONTEND_URL.strip().rstrip("/"))
        return list(origins)

settings = Settings()
