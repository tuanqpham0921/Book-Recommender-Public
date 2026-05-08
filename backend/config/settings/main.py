from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from .app import AppSettings
from .redis import RedisSettings
from .openai import OpenAISettings
from .postgres import PostgresSettings


class Settings(BaseModel):
    """Unified application settings (aggregates all sub-configs)."""

    model_config = SettingsConfigDict(env_file="config/.env", env_file_encoding="utf-8")

    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()
    openai: OpenAISettings = OpenAISettings()
    app: AppSettings = AppSettings()


settings = Settings()
