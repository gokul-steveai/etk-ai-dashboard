from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database configuration
    DATABASE_URL: str

    # Email configuration
    EMAIL_USER: str
    EMAIL_PASS: str

    # Authentication configuration
    SECRET_KEY: str = "TheSecretKey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    GOOGLE_CLIENT_ID: str

    # Stripe configuration
    FRONTEND_URL: str = "http://localhost:3000"
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str | None

    # Application configuration
    APP_NAME: str = "ETK AI"
    COMPANY_NAME: str = "ETK AI Inc."

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Keeps things stable if extra arguments exist in your .env
    )


settings = Settings()
