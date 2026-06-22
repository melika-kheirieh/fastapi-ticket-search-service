from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Ticket Search Service"
    environment: str = "local"
    database_url: str = (
        "postgresql+psycopg://ticket_user:ticket_password@localhost:5432/ticket_db"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()