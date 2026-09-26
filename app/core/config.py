"""Environment-only configuration. No secrets are emitted in logs."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./marketpulse.db"
    app_env: str = "development"
    log_level: str = "INFO"
    api_key: str = ""
    market_data_provider: str = "twelvedata"
    twelvedata_api_key: SecretStr = SecretStr("")
    allow_synthetic_data: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def settings() -> Settings:
    return Settings()
