# FastAPI Ticket Search Service

[![CI](https://github.com/melika-kheirieh/fastapi-ticket-search-service/actions/workflows/ci.yml/badge.svg)](https://github.com/melika-kheirieh/fastapi-ticket-search-service/actions/workflows/ci.yml)

A production-aware backend learning project for managing support tickets with PostgreSQL and searching them with Elasticsearch.

The core design idea is simple:

**PostgreSQL is the source of truth. Elasticsearch is a query-optimized search projection.**

This project is not just an Elasticsearch demo. It is a backend service that shows persistence, migrations, API design, search query construction, reindexing, tests, CI, and Docker-based verification.

## Features

- FastAPI REST API
- PostgreSQL persistence
- SQLAlchemy model, repository, and service layers
- Alembic migrations
- Ticket CRUD endpoints
- Filtering and pagination
- Elasticsearch explicit index mapping
- Full-text ticket search
- Isolated Elasticsearch query builder
- Reindex flow from PostgreSQL to Elasticsearch
- Unit/API tests with pytest
- Docker Compose local stack
- End-to-end search smoke script
- GitHub Actions CI with fast tests and Docker smoke verification

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Elasticsearch
- Docker Compose
- pytest
- GitHub Actions

## Architecture

```mermaid
flowchart LR
    Client["Client"] --> API["FastAPI API"]
    API --> DB["PostgreSQL"]
    API --> ES["Elasticsearch"]
    DB --> Reindex["Reindex Script"]
    Reindex --> ES
```

Application boundaries:

```text
Write path: API Router -> Service -> Repository -> PostgreSQL -> Elasticsearch sync
Search path: Search API -> Query Builder -> Elasticsearch
Repair path: Reindex Script -> PostgreSQL -> Elasticsearch
```

PostgreSQL owns the durable ticket state. Elasticsearch stores a derived search document that can be rebuilt from PostgreSQL if the search index becomes stale or unavailable.

## API Overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/tickets` | Create a ticket |
| `GET` | `/tickets` | List tickets with filters and pagination |
| `GET` | `/tickets/{ticket_id}` | Get one ticket |
| `PATCH` | `/tickets/{ticket_id}` | Update a ticket |
| `DELETE` | `/tickets/{ticket_id}` | Delete a ticket |
| `GET` | `/tickets/search` | Search tickets with Elasticsearch |

## Ticket Fields

A ticket contains:

- `id`
- `user_id`
- `title`
- `description`
- `status`
- `priority`
- `category`
- `tags`
- `created_at`
- `updated_at`

## Search Behavior

The search endpoint supports full-text search and exact filters.

Supported query parameters include:

| Parameter | Purpose |
| --- | --- |
| `q` | Full-text search across ticket title and description |
| `user_id` | Filter by ticket owner |
| `status` | Filter by ticket status |
| `priority` | Filter by priority |
| `category` | Filter by category |
| `tag` | Filter by one tag |
| `created_from` | Filter tickets created at or after this timestamp |
| `created_to` | Filter tickets created at or before this timestamp |
| `limit` | Limit result count |
| `offset` | Skip result count for pagination |

Example:

```bash
curl "http://localhost:8001/tickets/search?q=payment&status=open&tag=checkout&limit=10&offset=0"
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

Run tests:

```bash
pytest -q
```

Run the API locally without Docker:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

## Docker Compose

Build and start the full local stack:

```bash
docker compose up --build -d
```

Check service status:

```bash
docker compose ps -a
```

The API is available at:

```text
http://localhost:8001
```

OpenAPI docs:

```text
http://localhost:8001/docs
```

Stop the stack:

```bash
docker compose down
```

Remove local volumes when you need a clean reset:

```bash
docker compose down -v
```

Use `down -v` carefully in local development because it removes PostgreSQL and Elasticsearch volumes.

## Database Migrations

Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Check the current migration revision:

```bash
docker compose exec api alembic current
```

Create a new migration after model changes:

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
```

## Elasticsearch Setup

Create the Elasticsearch ticket index:

```bash
docker compose exec api python -m app.search.setup
```

Reindex tickets from PostgreSQL into Elasticsearch:

```bash
docker compose exec api python -m app.search.reindex
```

The reindex flow exists because Elasticsearch is treated as a rebuildable projection, not as the primary database.

## Smoke Tests

Run the ticket API smoke script:

```bash
bash scripts/verify_ticket_api.sh
```

Run the end-to-end search smoke script:

```bash
bash scripts/verify_search_flow.sh
```

The search smoke script verifies the main search flow from outside the application:

- the API is reachable;
- the Elasticsearch index exists;
- a ticket can be created through the API;
- the created ticket is synced into the search projection;
- the ticket can be found through the search endpoint.

By default, smoke scripts target:

```text
http://localhost:8001
```

You can override the target API URL when needed:

```bash
BASE_URL=http://localhost:8000 bash scripts/verify_search_flow.sh
```

## Testing

Run the test suite:

```bash
pytest -q
```

Current test coverage focuses on:

- ticket CRUD API behavior;
- service/repository boundaries;
- request validation;
- filtering and pagination;
- Elasticsearch mapping;
- Elasticsearch document conversion;
- Elasticsearch query building;
- search API behavior with fake search clients;
- reindex behavior.

The fast test suite is designed to run without a live PostgreSQL or Elasticsearch service.

## CI

GitHub Actions runs two validation jobs on pushes to `main` and on pull requests.

The `tests` job installs dependencies and runs the fast pytest suite.

The `docker-smoke` job runs after `tests`, starts the Docker Compose stack, executes the search smoke flow, prints Docker logs on failure, and tears the stack down.

This keeps fast feedback separate from the heavier end-to-end check.

## Design Decisions

### PostgreSQL is the source of truth

Ticket data is stored and updated in PostgreSQL. Elasticsearch is not treated as the primary database.

### Elasticsearch is a search projection

Search documents are derived from ticket records. If Elasticsearch becomes stale, the index can be rebuilt from PostgreSQL.

### Query building is isolated

Elasticsearch query construction lives in a separate module so search behavior can be tested without running Elasticsearch.

### Reindexing is explicit

The project includes a reindex command to rebuild the search projection from PostgreSQL. This makes the source-of-truth boundary visible and recoverable.

### Fast tests and smoke tests are separated

Fast tests run with pytest and focus on unit/API behavior. Smoke tests run against the Docker Compose stack and verify the main runtime flow.

### Current sync is intentionally simple

Ticket writes are synced to Elasticsearch after PostgreSQL writes. This is enough for the current phase, but it is not yet a production-grade reliability pattern.

The next reliability step is an outbox-based workflow for safer asynchronous indexing and retry handling.

## Out of Scope

This project does not currently include:

- authentication or authorization;
- outbox-based indexing;
- async indexing with Redis/Celery;
- advanced observability;
- production Elasticsearch cluster configuration;
- cloud deployment;
- semantic or hybrid search.

## Roadmap

Planned next steps:

- improve Elasticsearch failure handling;
- add an outbox table for reliable indexing events;
- add retry handling for failed search sync;
- add structured logging and lightweight observability;
- add semantic or hybrid search with embeddings;
- add Persian search quality improvements.
