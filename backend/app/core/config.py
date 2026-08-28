from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./finsense.db"
    JWT_SECRET_KEY: str = "dev-secret-change-in-prod-please-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AI_PROVIDER: str = "openai"
    AI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "FinSense <noreply@finsense.app>"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:5173"
    # Real SMTP / transactional email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True
    # Toggle: expose verification token in dev response only when SMTP not configured
    ENV: str = "development"

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

settings = Settings()
