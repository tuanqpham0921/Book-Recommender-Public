from pydantic_settings import BaseSettings, SettingsConfigDict


# In app/config/settings.py
class PostgresSettings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 5432
    DB: str = "book_recommender"
    USER: str = "postgres"
    PASSWORD: str = "password"
    MIN_CONNECTIONS: int = 5
    MAX_CONNECTIONS: int = 20

    @property
    def asyncpg_url(self) -> str:
        """URL for asyncpg connections."""
        if self.HOST.startswith("/cloudsql/"):
            # Cloud SQL socket connection
            return (
                f"postgresql://{self.USER}:{self.PASSWORD}@/{self.DB}?host={self.HOST}"
            )
        else:
            # TCP connection
            return f"postgresql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"

    @property
    def sqlalchemy_url(self) -> str:
        """URL for SQLAlchemy async connections."""
        if self.HOST.startswith("/cloudsql/"):
            # Cloud SQL socket connection
            return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@/{self.DB}?host={self.HOST}"
        else:
            # TCP connection
            return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_prefix="POSTGRES_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
