"""Application Configuration"""

import logging
import logging.config
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Documentation Platform"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    BASE_URL: str = "http://localhost:3000"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    AUDIENCE_AUDIT_HMAC_KEYS: str = "v1:dev-audience-audit-signing-key"
    AUDIENCE_AUDIT_ACTIVE_KEY_ID: str = "v1"
    AUDIENCE_ASSIGNMENT_SCHEMA_VERSION: str = "1.0.0"
    ACCOUNT_LOCKOUT_MAX_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    SESSION_INACTIVITY_DAYS: int = 30
    REVIEW_SLA_REMINDER_HOURS: int = 48
    REVIEW_SLA_ESCALATION_HOURS: int = 96

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # requests per window
    RATE_LIMIT_WINDOW: int = 60  # seconds
    ASSIGNMENT_RATE_LIMIT_REQUESTS: int = 30  # requests per window
    ASSIGNMENT_RATE_LIMIT_WINDOW: int = 60  # seconds
    OUTBOX_DEFAULT_MAX_ATTEMPTS: int = 5
    ASSIGNMENT_JOB_MAX_ATTEMPTS: int = 5
    ASSIGNMENT_JOB_RETRY_BASE_DELAY_SECONDS: int = 30
    ASSIGNMENT_JOB_RETRY_MAX_DELAY_SECONDS: int = 300
    ASSIGNMENT_JOB_RETRY_BACKOFF_MULTIPLIER: float = 2.0
    ASSIGNMENT_JOB_RETRY_JITTER_RATIO: float = 0.2
    TRUST_PROXY_HEADERS: bool = False
    TRUSTED_PROXY_IPS: list[str] = []

    # Database
    DATABASE_URL: str = "sqlite:///./data/portal.db"
    SQL_ECHO: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Storage (S3)
    S3_ENABLED: bool = False
    S3_BUCKET: str = "document-portal"
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"

    # Email (SMTP)
    EMAIL_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@portal.com"
    EMAIL_FROM_NAME: str = "Documentation Platform"

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set[str] = {".docx", ".pptx", ".txt"}
    LIBREOFFICE_BIN: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # Feature flags (architecture rollout safety)
    FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE: bool = True
    FEATURE_FLAG_PROJECTION_CACHE: bool = True
    FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT: bool = False
    FEATURE_FLAG_NEW_AUDIENCE_RULES: bool = False
    FEATURE_FLAG_NEW_AUDIENCE_RULES_ROLLOUT_PERCENTAGE: int = 0
    FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT: bool = True
    AUDIENCE_VALIDATION_SAFE_MODE_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# Configure structured logging
def setup_logging():
    """Configure application logging"""
    log_format = (
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        if settings.LOG_FORMAT == "json"
        else "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": log_format,
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"],
            },
            "loggers": {
                "uvicorn": {"level": "INFO"},
                "sqlalchemy": {"level": "WARNING"},
            },
        }
    )


# Initialize logging
setup_logging()
