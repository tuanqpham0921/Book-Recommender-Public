from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class AppSettings(BaseSettings):
    ENVIRONMENT: str = "development"  # dev | prod | test
    ALLOW_ORIGINS: List[str] = [
        "https://tuanqpham0921.com",
        "https://www.tuanqpham0921.com",
        "https://book-recommender-tuanqpham0921.web.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    EXPORT_DIR: str = "logs/"
    DATA_DIR: str = "data/"
    EXAMPLE_PROMPT_DIR: str = DATA_DIR + "prompt_example/"

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
