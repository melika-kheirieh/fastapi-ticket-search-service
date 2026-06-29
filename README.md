# FastAPI Ticket Search Service

[![CI](https://github.com/melika-kheirieh/fastapi-ticket-search-service/actions/workflows/ci.yml/badge.svg)](https://github.com/melika-kheirieh/fastapi-ticket-search-service/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-source%20of%20truth-336791)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-search%20projection-005571)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-local%20stack-2496ED)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)

A production-aware backend service for managing support tickets in PostgreSQL and making them searchable through an Elasticsearch projection.

The core design rule is intentionally simple:

**PostgreSQL is the durable source of truth. Elasticsearch is a rebuildable, query-optimized search projection.**

The service treats search as a rebuildable projection instead of coupling ticket writes directly to Elasticsearch. It shows API design, persistence, migrations, search mapping, query construction, outbox-based indexing, reindexing, structured logging, health checks, tests, and Docker Compose verification.

## What This Project Shows

- FastAPI ticket CRUD API with request/response schemas
- PostgreSQL persistence with SQLAlchemy repositories and Alembic migrations
- Database-backed ticket filtering and pagination
- Elasticsearch index mapping and full-text search
- Transactional outbox events for durable ticket-to-search synchronization
- Retryable outbox processor with failure metadata
- Celery worker and beat scheduler for scheduled outbox processing, backed by Redis
- Reindex command for rebuilding Elasticsearch from PostgreSQL
- Request id middleware and structured JSON logs
- Health checks for API liveness and search readiness
- Docker Compose stack with PostgreSQL, Redis, Elasticsearch, migrations, API, Celery worker, and Celery beat services
- pytest tests for API behavior, search query construction, indexing, reindexing, outbox events, Celery task behavior, and observability
- GitHub Actions CI

## Quick Review Path

| Start here | What it explains |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Source-of-truth boundary, outbox sync, search projection, and recovery model |
| [docs/operations.md](docs/operations.md) | Docker Compose startup, index setup, smoke verification, health checks, and logs |
| [docs/roadmap.md](docs/roadmap.md) | Completed work, next areas, and intentionally deferred scope |

## Current Status

| Area | Status | What is implemented |
| --- | --- | --- |
| Ticket API | Implemented | FastAPI CRUD endpoints with Pydantic request and response schemas |
| Persistence | Implemented | PostgreSQL, SQLAlchemy repositories, Alembic migrations, filters, and pagination |
| Search projection | Implemented | Elasticsearch `tickets_v1` mapping, setup command, query builder, and `/tickets/search` endpoint |
| Sync reliability | Implemented | Transactional outbox events, retry metadata, stuck-processing recovery, and reindex recovery path |
| Worker runtime | Implemented | Celery worker and Celery beat services using Redis as broker/backend in Docker Compose |
| Observability | Implemented | Request IDs, structured JSON logs, `/health`, and `/health/search` |
| Verification | Implemented | Focused pytest suite, GitHub Actions CI, and Docker Compose smoke verification |

Current intentional exclusions:

- Authentication and authorization
- Production deployment setup
- PostgreSQL FTS and Persian analyzer work
- Semantic or hybrid search
- A frontend dashboard

The current scope stays focused on backend reliability and search projection correctness.

## Architecture

Ticket writes commit the ticket row and the outbox event in the same PostgreSQL transaction:

```mermaid
flowchart TD
    A["Ticket API"] --> B["TicketService"]
    B --> C["tickets table"]
    B --> D["outbox_events table"]
````

The Celery worker updates Elasticsearch asynchronously, with Celery beat scheduling outbox batches:

```mermaid
flowchart TD
    A["Celery beat"] --> B["Schedule outbox batch"]
    B --> C["Celery worker claims ready events"]
    C --> D["Index or delete document"]
    D --> E["Mark processed"]
    D --> F["Mark failed with retry metadata"]
```

Search reads from the Elasticsearch projection:

```mermaid
flowchart TD
    A["GET /tickets/search"] --> B["Query builder"]
    B --> C["Elasticsearch tickets_v1"]
    C --> D["TicketResponse list"]
```

The projection can be rebuilt at any time from PostgreSQL:

```bash
python -m app.search.reindex
```

See [docs/architecture.md](docs/architecture.md) for design notes.

## Demo Flow

Start the full local stack:

```bash
docker compose up --build -d
```

Create the Elasticsearch index:

```bash
docker compose exec api python -m app.search.setup
```

Run the Celery-backed smoke flow:

```bash
scripts/verify_search_flow.sh
```

The smoke script verifies this path:

1. Create a ticket through the API.
2. Let the Celery worker sync it to Elasticsearch.
3. Search for the created ticket through `/tickets/search`.

## API Endpoints

Health checks:

```http
GET /health
GET /health/search
```

Ticket endpoints:

```http
POST /tickets
GET /tickets
GET /tickets/search
GET /tickets/{ticket_id}
PATCH /tickets/{ticket_id}
DELETE /tickets/{ticket_id}
```

Create a ticket:

```bash
curl -X POST "http://localhost:8001/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "Payment failed",
    "description": "Customer payment failed during checkout.",
    "status": "open",
    "priority": "high",
    "category": "billing",
    "tags": ["payment", "checkout"]
  }'
```

Filter tickets through PostgreSQL:

```bash
curl "http://localhost:8001/tickets?status=open&category=billing&limit=10&offset=0"
```

Search tickets through Elasticsearch:

```bash
curl "http://localhost:8001/tickets/search?q=payment&status=open&tag=checkout&limit=10&offset=0"
```

## Ticket Model

| Field         | Description                                     |
| ------------- | ----------------------------------------------- |
| `id`          | Database-generated ticket id                    |
| `user_id`     | Owner/user identifier                           |
| `title`       | Short ticket title                              |
| `description` | Longer searchable body                          |
| `status`      | Workflow status, for example `open` or `closed` |
| `priority`    | Priority value, for example `medium` or `high`  |
| `category`    | Support category, for example `billing`         |
| `tags`        | List of tag strings                             |
| `created_at`  | Creation timestamp                              |
| `updated_at`  | Last update timestamp                           |

## Database Filtering

The database-backed list endpoint supports exact filters and pagination:

| Query parameter | Description                                  |
| --------------- | -------------------------------------------- |
| `user_id`       | Filter by owner/user id                      |
| `status`        | Filter by ticket status                      |
| `priority`      | Filter by ticket priority                    |
| `category`      | Filter by ticket category                    |
| `limit`         | Maximum number of results, from `1` to `100` |
| `offset`        | Number of rows to skip, starting from `0`    |

## Elasticsearch Search

The search endpoint supports full-text search plus exact filters:

| Query parameter | Description                                        |
| --------------- | -------------------------------------------------- |
| `q`             | Full-text search across `title` and `description`  |
| `user_id`       | Filter by owner/user id                            |
| `status`        | Filter by status                                   |
| `priority`      | Filter by priority                                 |
| `category`      | Filter by category                                 |
| `tag`           | Filter by one tag                                  |
| `created_from`  | Filter tickets created at or after this timestamp  |
| `created_to`    | Filter tickets created at or before this timestamp |
| `limit`         | Maximum number of results, from `1` to `100`       |
| `offset`        | Number of rows to skip, starting from `0`          |

The Elasticsearch index is named:

```text
tickets_v1
```

The explicit mapping lives in [app/search/mappings.py](app/search/mappings.py).

Important mapping choices:

| Field         | Elasticsearch type             | Reason                                       |
| ------------- | ------------------------------ | -------------------------------------------- |
| `title`       | `text` with `keyword` subfield | Full-text search plus exact/sort-ready value |
| `description` | `text`                         | Full-text search                             |
| `status`      | `keyword`                      | Exact filtering                              |
| `priority`    | `keyword`                      | Exact filtering                              |
| `category`    | `keyword`                      | Exact filtering                              |
| `tags`        | `keyword`                      | Tag filtering                                |
| `user_id`     | `long`                         | Numeric owner filter                         |
| `created_at`  | `date`                         | Sorting and date ranges                      |
| `updated_at`  | `date`                         | Freshness tracking                           |

The query builder lives in [app/search/queries.py](app/search/queries.py). It builds a `bool` query with:

* `multi_match` over `title` and `description` when `q` is provided
* `term` filters for `status`, `priority`, `category`, `user_id`, and `tags`
* `range` filtering on `created_at`
* stable sorting by `created_at` and `id` in descending order
* `from` and `size` pagination

## Outbox and Reindexing

Ticket writes create outbox events in the same PostgreSQL transaction:

| API action                    | Outbox event     |
| ----------------------------- | ---------------- |
| `POST /tickets`               | `ticket.created` |
| `PATCH /tickets/{ticket_id}`  | `ticket.updated` |
| `DELETE /tickets/{ticket_id}` | `ticket.deleted` |

The Celery worker runs scheduled outbox batches. The processor claims pending or retryable events, writes the matching Elasticsearch document, deletes documents for deleted tickets, and marks each event as `processed` or `failed`.

Failed events keep:

* `retry_count`
* `last_error`
* `next_attempt_at`

That means an Elasticsearch outage does not lose the intent to update the search projection.

Run one local outbox-processing batch:

```bash
python -m app.outbox.cli
```

Rebuild the full search projection from PostgreSQL:

```bash
python -m app.search.reindex
```

## Observability

Every HTTP request gets a request id:

* incoming `X-Request-ID` is reused when present
* otherwise the API generates one
* the response includes `X-Request-ID`
* structured logs include the active `request_id`

Important operational logs use an `event` field:

| Event                       | Meaning                                            |
| --------------------------- | -------------------------------------------------- |
| `request_started`           | HTTP request entered the app                       |
| `request_completed`         | HTTP request completed successfully                |
| `request_failed`            | HTTP request raised an exception                   |
| `ticket_created`            | Ticket was created and an outbox event was written |
| `ticket_updated`            | Ticket was updated and an outbox event was written |
| `ticket_deleted`            | Ticket was deleted and an outbox event was written |
| `ticket_search_unavailable` | Search endpoint could not use Elasticsearch        |
| `ticket_index_failed`       | Outbox processor failed to sync a ticket document  |
| `outbox_event_processed`    | One outbox event was synced successfully           |
| `outbox_batch_processed`    | One outbox processing batch completed              |
| `reindex_completed`         | Full PostgreSQL-to-Elasticsearch reindex finished  |
| `search_health_failed`      | Search subsystem health check failed unexpectedly  |

Search subsystem status is exposed separately from the basic API health check:

```bash
curl http://localhost:8001/health/search
```

`/health` only checks that the API is alive. `/health/search` checks whether Elasticsearch is reachable and whether the configured ticket index exists.

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

Run migrations:

```bash
alembic upgrade head
```

Run the API locally:

```bash
uvicorn app.main:app --reload
```

Run one local outbox-processing batch:

```bash
python -m app.outbox.cli
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

The Compose setup starts:

* PostgreSQL
* Alembic migration container
* Redis
* Elasticsearch
* API
* Celery worker
* Celery beat scheduler

The API is exposed on:

```text
http://localhost:8001
```

Elasticsearch is exposed on:

```text
http://localhost:9200
```

Create the Elasticsearch ticket index inside the API container:

```bash
docker compose exec api python -m app.search.setup
```

Reindex tickets into Elasticsearch inside the API container:

```bash
docker compose exec api python -m app.search.reindex
```

Follow worker and beat logs:

```bash
docker compose logs -f worker
docker compose logs -f beat
```

Stop containers:

```bash
docker compose down
```

Remove local PostgreSQL and Elasticsearch data:

```bash
docker compose down -v
```

More operational commands are listed in [docs/operations.md](docs/operations.md).

## Database Migrations

Run migrations manually:

```bash
alembic upgrade head
```

Check the current revision:

```bash
alembic current
```

Check the current revision inside Docker:

```bash
docker compose exec api alembic current
```

The migration history currently includes:

* initial `tickets` table
* `outbox_events` table for durable search-sync events
* retry scheduling metadata for outbox events
* indexes for common ticket access patterns

## Configuration

Main environment variables:

| Variable                            | Purpose                                              |
| ----------------------------------- | ---------------------------------------------------- |
| `APP_NAME`                          | FastAPI application name                             |
| `ENVIRONMENT`                       | Runtime environment label                            |
| `DATABASE_URL`                      | SQLAlchemy database URL                              |
| `ELASTICSEARCH_URL`                 | Elasticsearch HTTP URL                               |
| `TICKET_SEARCH_INDEX`               | Elasticsearch index name                             |
| `LOG_LEVEL`                         | Python logging level                                 |
| `CELERY_BROKER_URL`                 | Redis URL used by Celery workers                     |
| `CELERY_RESULT_BACKEND`             | Redis URL used for Celery task results               |
| `OUTBOX_BATCH_SIZE`                 | Number of outbox events claimed per processing batch |
| `OUTBOX_MAX_RETRY_COUNT`            | Maximum attempts before an event stops being retried |
| `OUTBOX_PROCESSING_TIMEOUT_SECONDS` | Age after which `processing` events can be reclaimed |
| `OUTBOX_BEAT_SCHEDULE_SECONDS`      | Delay between scheduled outbox-processing tasks      |

Docker Compose uses:

```text
postgresql+psycopg://ticket_user:ticket_password@postgres:5432/ticket_db
```

```text
http://elasticsearch:9200
```

## Tests

Run tests:

```bash
pytest -q
```

The test suite is focused on unit/API behavior and does not require a live Elasticsearch instance.

Current coverage includes:

* ticket API behavior
* ticket filtering and pagination
* outbox events for create, update, and delete
* outbox claiming, retry scheduling, and stuck processing recovery
* Celery schedule configuration and outbox task behavior
* Elasticsearch mapping
* index creation
* ticket-to-search document conversion
* indexing and delete behavior
* reindexing from PostgreSQL
* search query construction
* search execution wrapper
* search API parameter forwarding and validation
* request id middleware
* search health states
* JSON log formatting

Run the Docker-based smoke flow after the stack is up:

```bash
scripts/verify_search_flow.sh
```

The script uses this default API URL:

```text
http://localhost:8001
```

Override it only when needed:

```bash
BASE_URL=http://localhost:8000 scripts/verify_search_flow.sh
```

## Repository Structure

```text
app/
  api/              FastAPI routers
  core/             configuration, logging, request context
  db/               SQLAlchemy base and session
  models/           SQLAlchemy models
  repositories/     database access layer
  schemas/          Pydantic request/response models
  search/           Elasticsearch client, mapping, query, indexer, reindex
  services/         ticket use cases
  tasks/            Celery task entrypoints
  outbox/           outbox processor and one-shot CLI
alembic/            database migrations
docs/               architecture, operations, and roadmap
scripts/            local verification scripts
tests/              pytest suite
```

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for detailed sequencing and future work.

Next areas include:

* lexical search maturity, PostgreSQL FTS, Persian analyzer work, and evaluation metrics
* embedding provider boundary, semantic search, hybrid search, and stronger evaluation
* meaningful JWT authorization and search data-access boundaries
* production polish and public documentation cleanup
