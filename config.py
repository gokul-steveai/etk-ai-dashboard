from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    EMAIL_USER: str
    EMAIL_PASS: str
    DATABASE_URL: str
    GOOGLE_CLIENT_ID: str
    SECRET_KEY: str = "TheSecretKey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Keeps things stable if extra arguments exist in your .env
    )


def load_config() -> Settings:
    return Settings()


settings = load_config()
