from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class AppSettings(BaseSettings):
    NAME: str
    ENVIRONMENT: str
    ALLOW_ORIGINS: str
    EXPORT_DIR: str
    DATA_DIR: str
    EXAMPLE_PROMPT_DIR: str

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
