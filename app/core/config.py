from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Ticket Search Service"
    environment: str = "local"
    database_url: str = (
        "postgresql+psycopg://ticket_user:ticket_password@localhost:5432/ticket_db"
    )
    elasticsearch_url: str = "http://localhost:9200"
    ticket_search_index: str = "tickets_v1"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()