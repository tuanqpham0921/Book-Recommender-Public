from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 6379

    @property
    def url(self) -> str:
        return f"redis://{self.HOST}:{self.PORT}"

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_prefix="REDIS_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
