"""
FRC System — Configuration
===========================
Loads all settings from environment variables.
Use .env for local dev; Render dashboard env vars for production.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Financial Intelligence Processing System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # MongoDB
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "frc_db"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Email / OTP (optional)
    SENDER_EMAIL: str = ""
    SENDER_PASSWORD: str = ""
    OTP_EXPIRY_MINUTES: int = 5

    # Case numbering
    CASE_NUMBER_PREFIX: str = "FRC"
    CASE_NUMBER_YEAR: int = 2026

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
