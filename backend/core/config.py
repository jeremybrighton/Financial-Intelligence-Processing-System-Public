"""
FRC System — Configuration
===========================
All settings loaded from environment variables.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Financial Intelligence Processing System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    MONGO_URI: str
    FRC_DB_NAME: str = "frc_db"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SENDER_EMAIL: str = ""
    SENDER_PASSWORD: str = ""
    OTP_EXPIRY_MINUTES: int = 5

    CORS_ORIGINS: str = (
        "https://fraud-detector-b.vercel.app,"
        "http://localhost:3000,"
        "http://localhost:3001"
    )

    API_KEY_LENGTH: int = 48
    DEFAULT_CTR_THRESHOLD_USD: float = 15000.0
    DEFAULT_CBT_THRESHOLD_USD: float = 10000.0
    DEFAULT_SAR_ML_THRESHOLD: float = 0.70

    REPORT_EXPORT_DIR: str = "/tmp/frc_reports"
    LEGAL_DATA_DIR: str = "legal/structured"
    CASE_NUMBER_PREFIX: str = "FRC"
    CASE_NUMBER_YEAR: int = 2026

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
