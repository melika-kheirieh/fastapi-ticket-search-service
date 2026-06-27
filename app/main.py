from fastapi import FastAPI

from app.api.tickets import router as tickets_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A PostgreSQL-backed ticket service with Elasticsearch search projection.",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(tickets_router)
