from pydantic_settings import BaseSettings, SettingsConfigDict
from config.constants import FilesLocationConstants

class SQLAlchemySettings(BaseSettings):
    """Connection and pool settings for the async SQLAlchemy engine (PostgreSQL + asyncpg)."""

    HOST: str
    PORT: int
    DB: str
    USER: str
    PASSWORD: str
    MIN_CONNECTIONS: int
    MAX_CONNECTIONS: int

    @property
    def sqlalchemy_url(self) -> str:
        """Async SQLAlchemy URL (postgresql+asyncpg)."""
        if self.HOST.startswith("/cloudsql/"):
            # Cloud SQL socket connection
            return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@/{self.DB}?host={self.HOST}"
        else:
            # TCP connection
            return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"

    model_config = SettingsConfigDict(
        env_file=FilesLocationConstants.ENV_FILE,
        env_prefix="POSTGRES_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
