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

The service treats search as a rebuildable projection instead of coupling ticket writes directly to Elasticsearch. It shows API design, persistence, migrations, ownership authorization, search mapping and query construction, outbox-based indexing, reindexing, observability, tests, and Docker Compose verification.

## What This Project Shows

- FastAPI ticket CRUD API with request/response schemas
- PostgreSQL persistence with SQLAlchemy repositories and Alembic migrations
- Database-backed ticket filtering and pagination
- Elasticsearch index mapping and full-text search
- Transactional outbox events for durable ticket-to-search synchronization
- Retryable outbox processor with failure metadata
- Celery worker and beat scheduler for scheduled outbox processing, backed by Redis
- Reindex command for rebuilding Elasticsearch from PostgreSQL
- Header-based current-user context with `user` and `admin` roles
- Ownership authorization across create, list, get, update, delete, and search, including prevention of cross-user exposure through Elasticsearch
- Request ID middleware, structured JSON logs for the API process, and Prometheus-compatible HTTP, search, and outbox metrics
- Health checks for API liveness and Elasticsearch reachability
- Docker Compose stack with PostgreSQL, Redis, Elasticsearch, migrations, and non-root API, Celery worker, and Celery beat services
- `.env.example` with local configuration defaults
- Docker smoke verification for runtime users, metrics, outbox processing, authenticated API access, and search
- pytest coverage across API behavior, authentication context, authorization, search, indexing, outbox processing, Celery tasks, metrics, and observability
- GitHub Actions CI

## Quick Review Path

| Start here | What it explains |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Runtime boundaries, authorization, outbox consistency, search projection, metrics, and recovery |
| [docs/operations.md](docs/operations.md) | Local identity headers, Docker Compose, metrics, smoke verification, troubleshooting, and production boundaries |
| [docs/roadmap.md](docs/roadmap.md) | Completed reliability work, current hardening, future search phases, and deferred deployment scope |

## Current Status

| Area | Status | What is implemented |
| --- | --- | --- |
| Ticket API | Implemented | FastAPI CRUD endpoints with Pydantic request and response schemas |
| Persistence | Implemented | PostgreSQL, SQLAlchemy repositories, Alembic migrations, filters, and pagination |
| Search projection | Implemented | Elasticsearch `tickets_v1` mapping, setup command, query builder, and `/tickets/search` endpoint |
| Sync reliability | Implemented | Transactional outbox events, retry metadata, stuck-processing recovery, and reindex recovery path |
| Worker runtime | Implemented | Celery worker and Celery beat services using Redis as broker/backend in Docker Compose |
| Authorization | Implemented | Header-derived `user` and `admin` context with ownership enforced across PostgreSQL-backed CRUD/list access and Elasticsearch-backed search |
| Observability | Implemented | Request IDs, structured JSON logs for the API process, `/health`, `/health/search`, `/metrics`, and Prometheus-compatible HTTP, search, and outbox metrics |
| Container runtime | Implemented | Application containers run as a non-root `app` user |
| Verification | Implemented | Focused pytest suite, GitHub Actions CI, and Docker smoke verification covering runtime users, metrics, outbox processing, authenticated API access, and search |

Current intentional exclusions:

- Production identity provider integration
- JWT login and refresh-token flow
- Password-based authentication
- Production secrets management
- Kubernetes deployment
- Prometheus server deployment
- Alertmanager
- Grafana dashboards
- PostgreSQL full-text search
- Persian analyzer and lexical evaluation
- Semantic and hybrid search
- Frontend dashboard

The implemented boundary authorizes a header-derived current user and role. Those headers are a demo authentication mechanism, not a production authentication system; production identity verification and credential flows remain future work.

## Architecture

The diagrams below summarize the main runtime flow: PostgreSQL keeps durable ticket state, Celery and Redis process outbox batches asynchronously, and Elasticsearch remains a rebuildable search projection.

Ticket writes commit the ticket row and the outbox event in the same PostgreSQL transaction:

```mermaid
flowchart TD
    A["Ticket API"] --> B["TicketService"]
    B --> C["tickets table"]
    B --> D["outbox_events table"]
```

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
    A["GET /tickets/search"] --> B["Current-user context"]
    B --> C["Resolve visible user_id"]
    C --> D["Query builder"]
    D --> E["Elasticsearch tickets_v1 projection"]
    E --> F["Authorized results"]
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

1. Confirm that the API, worker, and beat run as the non-root `app` user.
2. Confirm that HTTP and outbox metrics are exposed.
3. Create a ticket through the API with a current-user header.
4. Wait for the Celery worker to process its outbox event.
5. Search for the created ticket with the same current-user header and confirm search metrics.

## API Endpoints

Health checks:

```http
GET /health
GET /health/search
```

Operational endpoint:

```http
GET /metrics
```

`/metrics` exposes operational instrumentation; it is not part of the ticket business API.

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
  -H "X-User-ID: 1" \
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
curl "http://localhost:8001/tickets?status=open&category=billing&limit=10&offset=0" \
  -H "X-User-ID: 1"
```

Search tickets through Elasticsearch:

```bash
curl "http://localhost:8001/tickets/search?q=payment&status=open&tag=checkout&limit=10&offset=0" \
  -H "X-User-ID: 1"
```

An admin may list tickets across users:

```bash
curl "http://localhost:8001/tickets?limit=10&offset=0" \
  -H "X-User-ID: 1" \
  -H "X-User-Role: admin"
```

## Authentication and Authorization Boundary

Protected ticket endpoints require `X-User-ID`. `X-User-Role` is optional, defaults to `user`, and supports only `user` and `admin`.

Regular users can create, list, get, update, delete, and search only their own tickets. A regular user who tries to create a ticket whose payload `user_id` belongs to another user receives `403`. An admin can access tickets belonging to any user.

A direct get, update, or delete request for another user's ticket returns `404`, avoiding disclosure of whether that resource exists. A regular user who explicitly requests another user's `user_id` in list or search receives `403`. Missing or invalid authentication context returns `401`.

Elasticsearch search enforces the same ownership boundary as PostgreSQL-backed API access; it is not a path around authorization. The API resolves the visible `user_id` and rejects a forbidden scope before it constructs or executes the Elasticsearch query.

The headers supply demo authentication context; the API uses that context for authorization. They are not a replacement for JWT, OAuth, password authentication, or a production identity provider.

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

Regular users are automatically restricted to their current `user_id`; the API does not trust a regular user's requested ownership scope. A regular user cannot request another user's data. Admins may specify `user_id` to select one owner or omit it to access tickets across users.

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

Ownership is resolved before the Elasticsearch query is executed. Regular-user searches always include the current user's identifier, while admin searches may select one user or span multiple users. Elasticsearch cannot bypass the API authorization boundary: search is an eventually consistent projection, but ownership enforcement is required on every query.

The Elasticsearch index is named:

```text
tickets_v1
```

The explicit mapping lives in [app/search/mappings.py](app/search/mappings.py).

Important mapping choices:

| Field         | Elasticsearch type             | Reason                                       |
| ------------- | ------------------------------ | -------------------------------------------- |
| `title`       | `text`                         | Full-text search                             |
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

## Metrics

Prometheus-compatible metrics are exposed at:

```http
GET /metrics
```

The endpoint includes:

* `http_requests_total`
* `http_request_duration_seconds`
* `search_requests_total`
* `search_unavailable_total`
* `search_request_duration_seconds`
* `outbox_events_by_status`

For matched endpoints, HTTP metrics use the request method, route template, and status. Query strings and explicit identifiers such as `request_id`, `ticket_id`, and `user_id` are not added as metric labels.

The project exposes Prometheus-compatible instrumentation. It does not currently deploy a Prometheus server, Alertmanager, or Grafana.

## Observability

Every HTTP request gets a request ID:

* incoming `X-Request-ID` is reused when present
* otherwise the API generates one
* the response includes `X-Request-ID`
* API logs emitted during the request include the active `request_id`

The API process configures JSON logging. Application logging calls attach
operational `event` fields, while Celery controls the worker and beat output
format:

| Event                              | Meaning                                             |
| ---------------------------------- | --------------------------------------------------- |
| `request_started`                  | HTTP request entered the API                        |
| `request_completed`                | HTTP request completed successfully                 |
| `request_failed`                   | HTTP request raised an exception                    |
| `ticket_created`                   | Ticket was created and an outbox event was written  |
| `ticket_updated`                   | Ticket was updated and an outbox event was written  |
| `ticket_deleted`                   | Ticket was deleted and an outbox event was written  |
| `ticket_search_unavailable`        | Search endpoint could not use Elasticsearch         |
| `outbox_events_claimed`            | An outbox batch was claimed for processing           |
| `outbox_event_processing_started`  | Processing started for one outbox event              |
| `outbox_event_processing_failed`   | One outbox event failed and received retry metadata  |
| `outbox_event_processed`           | One outbox event was synchronized successfully       |
| `outbox_batch_processed`           | One outbox processing batch completed                |

The reindex command reports its completion count to standard output. The search
health endpoint returns status details in its HTTP response; neither path
currently emits a dedicated completion/failure event.

Search subsystem status is exposed separately from the basic API health check:

```bash
curl http://localhost:8001/health/search
```

`/health` only checks that the API is alive. `/health/search` checks Elasticsearch reachability with a ping; the current implementation does not separately verify that the configured ticket index exists.

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

The API, worker, and beat application containers run as the non-root `app` user.

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

Copy `.env.example` when preparing local environment values. Main environment variables:

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
| `OUTBOX_BEAT_SCHEDULE_SECONDS`      | Declared schedule setting; the current Celery beat entry remains fixed at 10 seconds |

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

At a high level, pytest coverage includes:

* ticket API behavior, filtering, pagination, and authentication-context validation
* regular-user/admin authorization, ownership enforcement, and search authorization
* `401`, `403`, and ownership-hidden `404` behavior
* transactional outbox writes, processing, retry scheduling, and stuck-event recovery
* Elasticsearch mapping, query construction, indexing, deletion, and full reindexing
* request IDs, search health behavior, and HTTP/search/outbox metrics
* Celery configuration and task behavior

Separately, the Docker smoke flow verifies non-root runtime, metrics exposure, authenticated ticket creation, outbox processing, and Elasticsearch search.

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

The smoke flow checks non-root application runtime, metrics, authenticated ticket creation and search, outbox processing, and Elasticsearch projection behavior. Its protected API requests include `X-User-ID`.

## Repository Structure

```text
app/
  api/              FastAPI routers
  auth/             Current-user context and authorization models
  core/             configuration, logging, request context
  db/               SQLAlchemy base and session
  models/           SQLAlchemy models
  observability/    Prometheus-compatible metrics
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

Completed:

* Prometheus-compatible instrumentation
* Header-based current-user context
* Ownership authorization across the API and search
* Non-root application runtime
* Docker smoke verification

Still future work:

* JWT-based authentication
* Login and password management
* Production identity provider integration
* Prometheus deployment, Alertmanager, and Grafana
* Lexical evaluation and a Persian analyzer
* Semantic and hybrid search
* Production deployment hardening
