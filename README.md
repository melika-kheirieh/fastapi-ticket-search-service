# FastAPI Ticket Search Service

A backend project for building a ticket management and search service with FastAPI, PostgreSQL, Alembic, Elasticsearch, Docker Compose, and tests.

## Goal

This project demonstrates a database-backed backend service where PostgreSQL is the source of truth and Elasticsearch is later used as a search projection.

The important design idea is that the main ticket data should live in PostgreSQL. Elasticsearch will be added later as a query-optimized projection for search, not as the primary database.

## Current Status

Day 1 bootstrap is implemented:

- FastAPI application
- Health endpoint
- Basic environment-based configuration
- Dockerfile
- Docker Compose setup with API and PostgreSQL
- Minimal project documentation

Implemented endpoint:

```http
GET /health
```

Expected response:

```json
{"status":"ok"}
```

## Local Development

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If package downloads are unstable, use the configured mirror manually:

```bash
python -m pip install \
  --prefer-binary \
  --retries 10 \
  --timeout 120 \
  --index-url https://package-mirror.liara.ir/repository/pypi/simple \
  --extra-index-url https://pypi.org/simple \
  -r requirements.txt
```

Run the app locally:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

## Docker Compose

Build and run the API with PostgreSQL:

```bash
docker compose up --build
```

Then check the API:

```bash
curl http://localhost:8000/health
```

Stop containers:

```bash
docker compose down
```

Remove PostgreSQL data volume if you need a clean local reset:

```bash
docker compose down -v
```

## Configuration

Example environment variables are available in `.env.example`.

Current variables:

- `APP_NAME`
- `ENVIRONMENT`
- `DATABASE_URL`

The default local Docker database URL is:

```text
postgresql+psycopg://ticket_user:ticket_password@postgres:5432/ticket_db
```

## Planned Scope

This project is planned to include:

- Ticket CRUD API
- PostgreSQL persistence
- SQLAlchemy model, repository, and service layers
- Alembic migrations
- Database filtering and pagination
- Elasticsearch explicit mapping
- Elasticsearch search endpoint
- Reindex script from PostgreSQL to Elasticsearch
- Tests and CI

## Not Implemented Yet

The following are intentionally not implemented in Day 1:

- Ticket model
- Database session
- Alembic migrations
- Ticket CRUD endpoints
- Elasticsearch integration
- Redis, Celery, or async indexing
- Authentication
