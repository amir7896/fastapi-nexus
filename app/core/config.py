from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Nexus"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    API_V1_PREFIX: str = "/api/v1"

    # Comma separated list, e.g. "http://localhost:3000,http://localhost:5173"
    CORS_ORIGINS: str = "*"

    PASSWORD_HASH_ITERATIONS: int = 260000

    DATABASE_URL: str = "mysql+pymysql://root:password@127.0.0.1:3306/nexus"

    JWT_SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_CURRENCY: str = "usd"
    STRIPE_SUCCESS_URL: str = "http://localhost:5173/payment/success"
    STRIPE_CANCEL_URL: str = "http://localhost:5173/payment/cancel"
    # Customer-paid card processing fee (US cards: 2.9% + $0.30)
    STRIPE_FEE_PERCENT: Decimal = Decimal("2.9")
    STRIPE_FEE_FIXED: Decimal = Decimal("0.30")

    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "Nexus <onboarding@resend.dev>"
    PASSWORD_RESET_URL: str = "http://localhost:5173/reset-password"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_URL: str = "http://localhost:5173/verify-email"
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 1440  # 24 hours
    REQUIRE_EMAIL_VERIFICATION: bool = True

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY.strip())

    @property
    def resend_enabled(self) -> bool:
        return bool(self.RESEND_API_KEY.strip())

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
