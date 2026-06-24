# FastAPI Ticket Search Service

A backend service for managing support tickets with FastAPI, PostgreSQL, SQLAlchemy, Alembic, Docker Compose, and Elasticsearch.

The core design choice is:

```text
PostgreSQL = source of truth
Elasticsearch = rebuildable search projection
```

This project focuses on practical backend fundamentals: clear API contracts, database-backed persistence, explicit migrations, layered architecture, testable search queries, and a small smoke flow for demo verification.

## Features

- Ticket CRUD API
- PostgreSQL persistence with SQLAlchemy
- Alembic migrations and database indexes
- Repository and service layers
- Database filtering and pagination
- Elasticsearch `tickets_v1` index with explicit mapping
- Ticket write sync to Elasticsearch after create, update, and delete
- Reindex command to rebuild Elasticsearch from PostgreSQL
- Elasticsearch-backed search endpoint with full-text search and filters
- API, service, repository, and search-layer tests
- Docker Compose local stack
- GitHub Actions CI
- Search smoke verification script

Not implemented:

- Authentication

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy
- Alembic
- Pydantic
- Elasticsearch 8
- Docker Compose
- pytest
- GitHub Actions

## Architecture

Write path:

```text
API route
  -> service layer
  -> repository layer
  -> PostgreSQL
```

Search projection:

```text
Ticket write
  -> PostgreSQL commit
  -> search document
  -> Elasticsearch tickets_v1 document
```

Consistency rule:

- Ticket writes are committed to PostgreSQL first.
- Elasticsearch sync runs after the PostgreSQL commit.
- If Elasticsearch sync fails, the API write still succeeds and the failure is logged.
- The search projection can be rebuilt with the reindex command.

## API

Health:

```http
GET /health
```

Tickets:

```http
POST /tickets
GET /tickets
GET /tickets/{ticket_id}
PATCH /tickets/{ticket_id}
DELETE /tickets/{ticket_id}
```

Search:

```http
GET /tickets/search
```

Database-backed ticket listing supports:

| Parameter | Description |
| --- | --- |
| `user_id` | Filter by ticket owner |
| `status` | Filter by status |
| `priority` | Filter by priority |
| `category` | Filter by category |
| `limit` | Result limit, from `1` to `100` |
| `offset` | Number of rows to skip |

Elasticsearch-backed search supports:

| Parameter | Description |
| --- | --- |
| `q` | Full-text search across title and description |
| `user_id` | Filter by ticket owner |
| `status` | Filter by status |
| `priority` | Filter by priority |
| `category` | Filter by category |
| `tag` | Filter by one tag |
| `created_from` | Filter by minimum creation timestamp |
| `created_to` | Filter by maximum creation timestamp |
| `limit` | Result limit, from `1` to `100` |
| `offset` | Number of rows to skip |

Example:

```bash
curl "http://localhost:8001/tickets/search?q=payment&status=open&tag=checkout&limit=10&offset=0"
```

## Elasticsearch

The first search index is:

```text
tickets_v1
```

The mapping lives in:

```text
app/search/mappings.py
```

Important field choices:

| Field | Type | Purpose |
| --- | --- | --- |
| `title` | `text` with `keyword` subfield | Full-text search plus exact option |
| `description` | `text` | Full-text search |
| `status` | `keyword` | Exact filtering |
| `priority` | `keyword` | Exact filtering |
| `category` | `keyword` | Exact filtering |
| `tags` | `keyword` | Tag filtering |
| `user_id` | `long` | Numeric owner filter |
| `created_at` | `date` | Sorting and date ranges |
| `updated_at` | `date` | Freshness tracking |

Create the index:

```bash
python -m app.search.setup
```

Rebuild the search projection:

```bash
python -m app.search.reindex
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

Run the API locally:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

## Docker Compose

Build and start the local stack:

```bash
docker compose up --build -d
```

The stack includes:

- PostgreSQL
- Alembic migration container
- Elasticsearch
- API

The API is exposed on:

```text
http://localhost:8001
```

Elasticsearch is exposed on:

```text
http://localhost:9200
```

Run setup and reindex inside the API container:

```bash
docker compose exec api python -m app.search.setup
docker compose exec api python -m app.search.reindex
```

Run the search smoke flow:

```bash
scripts/verify_search_flow.sh
```

The smoke script checks API health, ensures the Elasticsearch index exists, creates a ticket through the API, reindexes tickets, and verifies that the created ticket is searchable through `GET /tickets/search`.

Stop containers:

```bash
docker compose down
```

Remove local PostgreSQL and Elasticsearch data:

```bash
docker compose down -v
```

## Migrations

Run migrations manually:

```bash
alembic upgrade head
```

Check current revision:

```bash
alembic current
```

Inside Docker:

```bash
docker compose exec api alembic current
```

Current migration history includes:

- initial `tickets` table
- indexes for common access patterns:
  - `user_id`
  - `status`
  - `category`
  - `created_at`

## Tests

Run tests:

```bash
pytest -q
```

Test coverage:

| Area | Coverage |
| --- | --- |
| API routes | CRUD routes, validation errors, not-found behavior, route-to-service contracts |
| Service layer | Ticket write behavior and Elasticsearch sync failure tolerance |
| Repository layer | SQLAlchemy filters, ordering, and pagination |
| Search documents | Conversion from database tickets to Elasticsearch documents |
| Search mapping | Explicit field mapping for full-text and filter fields |
| Search queries | Bool query construction, filters, date ranges, sorting, and pagination |
| Searcher | Elasticsearch response parsing |
| Reindex | Rebuilding the search projection from database tickets |
| Smoke script | Docker-backed API, PostgreSQL, and Elasticsearch search flow |

## CI

GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

It runs on pushes to `main` and on pull requests:

- sets up Python 3.12
- installs dependencies from `requirements.txt`
- runs `pytest -q`

## What This Demonstrates

- Designing PostgreSQL as the durable source of truth
- Using Elasticsearch as a rebuildable search projection
- Keeping API, service, repository, and search responsibilities separate
- Writing tests at different levels instead of relying only on end-to-end checks
- Handling eventual consistency between database writes and search indexing
- Packaging a backend project with Docker Compose, CI, migrations, and smoke verification