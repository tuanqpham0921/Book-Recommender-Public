from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    API_KEY: str
    BASE_MODEL: str = "gpt-4.1-mini"
    TOKENIZER_ENCODING: str = "o200k_base"

    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1024

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_prefix="OPENAI_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
