from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
class AppSettings(BaseSettings):
    ENVIRONMENT: str         = "development"  # dev | prod | test
    ALLOW_ORIGINS: List[str] = ["*"]
    EXPORT_DIR: str          = "logs/"
    DATA_DIR: str            = "data/"
    EXAMPLE_PROMPT_DIR: str  = DATA_DIR + "prompt_example/"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", env_file_encoding="utf-8", extra="ignore")