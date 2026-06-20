from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Ticket Search Service"
    environment: str = "local"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/tickets_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
