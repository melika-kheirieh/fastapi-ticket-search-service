from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Ticket Search Service",
    version="0.1.0",
    description="A PostgreSQL-backed ticket service with Elasticsearch search projection.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}