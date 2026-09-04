from functools import lru_cache
from decimal import Decimal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_DEFAULT = "change-me-in-production-use-a-long-random-string"


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

    JWT_SECRET_KEY: str = _INSECURE_JWT_DEFAULT
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
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 15  # OTP validity
    REQUIRE_EMAIL_VERIFICATION: bool = True
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15
    # Kept for optional frontend deep links; emails now send OTP codes only.
    PASSWORD_RESET_URL: str = "http://localhost:5173/reset-password"
    EMAIL_VERIFICATION_URL: str = "http://localhost:5173/verify-email"

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

    @model_validator(mode="after")
    def _reject_insecure_production_settings(self) -> "Settings":
        if not self.is_production:
            return self
        if self.JWT_SECRET_KEY.strip() in {"", _INSECURE_JWT_DEFAULT}:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong secret in production"
            )
        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must not include '*' in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
