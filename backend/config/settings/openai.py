from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    API_KEY: str
    BASE_MODEL: str
    TOKENIZER_ENCODING: str

    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSIONS: int

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_prefix="OPENAI_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
