from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from .app import AppSettings
from .openai import OpenAISettings
from .sqlalchemy import SQLAlchemySettings

from config.constants import FilesLocationConstants

class Settings(BaseModel):
    """Unified application settings (aggregates all sub-configs)."""

    model_config = SettingsConfigDict(
        env_file=FilesLocationConstants.ENV_FILE, 
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    sqlalchemy: SQLAlchemySettings = SQLAlchemySettings()
    openai: OpenAISettings = OpenAISettings()
    app: AppSettings = AppSettings()


settings = Settings()
