from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from config.constants import FilesLocationConstants

class AppSettings(BaseSettings):
    NAME: str
    ENVIRONMENT: str
    ALLOW_ORIGINS: str

    model_config = SettingsConfigDict(
        env_file=FilesLocationConstants.ENV_FILE,
        env_prefix="APP_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
