from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "Dental Saas Backend System"
    APP_DESCRIPTION: str = (
        "A digital system where you can manage your patients and appointments"
    )
    API_PREFIX: str = "/api/v1"

    DEBUG: bool = False
    ENV: str = "dev"
    DATABASE_URL: str
    REDIS_URL: str

    JWT_SECRET_KEY: SecretStr = SecretStr("")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


settings = Settings()