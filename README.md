# FastAPI Ticket Search Service

A production-aware backend learning project for managing support tickets and searching them with PostgreSQL and Elasticsearch.

PostgreSQL is the source of truth. Elasticsearch is used as a query-optimized search projection.

## Features

- FastAPI REST API
- PostgreSQL persistence
- SQLAlchemy repository/service layers
- Alembic migrations
- Ticket CRUD endpoints
- Filtering and pagination
- Elasticsearch explicit mapping
- Full-text ticket search
- Reindex flow from PostgreSQL to Elasticsearch
- Unit/API tests with pytest
- GitHub Actions CI
- Docker Compose local stack
- End-to-end search smoke script

## Tech Stack

- Python
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
````

Application boundaries:

```text
API Router -> Service -> Repository -> PostgreSQL
Search API -> Query Builder -> Elasticsearch
Reindex Script -> PostgreSQL -> Elasticsearch
```

## API Overview

| Method   | Endpoint               | Purpose                           |
| -------- | ---------------------- | --------------------------------- |
| `GET`    | `/health`              | Health check                      |
| `POST`   | `/tickets`             | Create a ticket                   |
| `GET`    | `/tickets`             | List tickets with filters         |
| `GET`    | `/tickets/{ticket_id}` | Get one ticket                    |
| `PATCH`  | `/tickets/{ticket_id}` | Update a ticket                   |
| `DELETE` | `/tickets/{ticket_id}` | Delete a ticket                   |
| `GET`    | `/tickets/search`      | Search tickets with Elasticsearch |

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

## Docker Compose

Build and start the stack:

```bash
docker compose up --build
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

## Database Migrations

Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Create a new migration after model changes:

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
```

## Elasticsearch Setup

Create or update the Elasticsearch index:

```bash
docker compose exec api python -m app.search.setup
```

Reindex tickets from PostgreSQL into Elasticsearch:

```bash
docker compose exec api python -m app.search.reindex
```

## Search Smoke Test

Run the end-to-end search verification script:

```bash
chmod +x scripts/verify_search_flow.sh
scripts/verify_search_flow.sh
```

The script verifies that:

* the API is reachable;
* the Elasticsearch index exists;
* a ticket can be created through the API;
* tickets can be reindexed from PostgreSQL;
* the created ticket can be found through Elasticsearch search.

## Testing

Run the test suite:

```bash
pytest -q
```

Current test coverage focuses on:

* ticket CRUD API behavior;
* service/repository boundaries;
* request validation;
* filtering and pagination;
* Elasticsearch query building;
* search API behavior with fake search clients.

## CI

GitHub Actions runs the test suite on pushes and pull requests.

The CI workflow is intentionally lightweight: it runs fast tests without requiring a live PostgreSQL or Elasticsearch service.

The Docker-based smoke script remains a manual integration check for the full local stack.

## Design Decisions

### PostgreSQL is the source of truth

Ticket data is stored and updated in PostgreSQL. Elasticsearch is not treated as the primary database.

### Elasticsearch is a search projection

Search documents are derived from ticket records. If Elasticsearch becomes stale, the index can be rebuilt from PostgreSQL.

### Query building is isolated

Elasticsearch query construction lives in a separate module so it can be tested without running Elasticsearch.

### Integration checks are explicit

Fast tests run in CI. The full PostgreSQL + Elasticsearch flow is verified separately with a smoke script.

## Out of Scope

This project does not currently include:

* authentication or authorization;
* async indexing with Redis/Celery;
* production Elasticsearch cluster configuration;
* observability stack;
* deployment to cloud infrastructure.