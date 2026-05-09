from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from .app import AppSettings
from .openai import OpenAISettings
from .sqlalchemy import SQLAlchemySettings


class Settings(BaseModel):
    """Unified application settings (aggregates all sub-configs)."""

    model_config = SettingsConfigDict(env_file="config/.env", env_file_encoding="utf-8")
    
    sqlalchemy: SQLAlchemySettings = SQLAlchemySettings()
    openai: OpenAISettings = OpenAISettings()
    app: AppSettings = AppSettings()


settings = Settings()
