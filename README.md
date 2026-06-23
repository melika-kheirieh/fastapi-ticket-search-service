# FastAPI Ticket Search Service

A backend service for managing support tickets with FastAPI, PostgreSQL, SQLAlchemy, Alembic, and Docker Compose.

The project is designed around a production-style separation of concerns: PostgreSQL is the source of truth for ticket data, while search-specific infrastructure can be added later as a separate projection layer.

## Current Scope

Implemented:

- FastAPI application
- PostgreSQL persistence
- SQLAlchemy ticket model
- Repository and service layers
- Alembic migrations
- Ticket CRUD API
- Database filters and pagination
- Database indexes for common ticket filters
- Docker Compose startup flow
- One-shot migration container
- Ticket API smoke verification script

Not implemented yet:

- Elasticsearch integration
- Search index mapping
- Reindexing from PostgreSQL to Elasticsearch
- Authentication
- CI pipeline

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy
- Alembic
- Pydantic
- Docker Compose

## Architecture Overview

The current application follows a simple layered structure:

```text
API routes
  -> service layer
  -> repository layer
  -> PostgreSQL
````

The API layer handles HTTP-specific concerns such as request validation and response status codes.

The service layer coordinates ticket use cases.

The repository layer owns database queries and keeps SQLAlchemy access out of the route handlers.

Alembic manages schema changes through versioned migrations.

## API Endpoints

Health check:

```http
GET /health
```

Ticket endpoints:

```http
POST /tickets
GET /tickets
GET /tickets/{ticket_id}
PATCH /tickets/{ticket_id}
DELETE /tickets/{ticket_id}
```

The ticket list endpoint supports database-backed filtering and pagination:

| Query parameter | Description                                  |
| --------------- | -------------------------------------------- |
| `user_id`       | Filter tickets by owner/user id              |
| `status`        | Filter tickets by status                     |
| `priority`      | Filter tickets by priority                   |
| `category`      | Filter tickets by category                   |
| `limit`         | Maximum number of results, from `1` to `100` |
| `offset`        | Number of rows to skip, starting from `0`    |

Example:

```bash
curl "http://localhost:8001/tickets?status=open&category=auth&limit=10&offset=0"
```

## Ticket Model

A ticket includes:

* `id`
* `user_id`
* `title`
* `description`
* `status`
* `priority`
* `category`
* `tags`
* `created_at`
* `updated_at`

## Local Development

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
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

Build and start the full local stack:

```bash
docker compose up --build -d
```

Check service status:

```bash
docker compose ps -a
```

The Compose setup starts services in this order:

1. PostgreSQL starts and becomes healthy.
2. Alembic migrations run in a one-shot `migrate` container.
3. The API starts only after migrations complete successfully.

The API is exposed on:

```text
http://localhost:8001
```

Health check:

```bash
curl http://localhost:8001/health
```

Stop containers:

```bash
docker compose down
```

Remove local PostgreSQL data:

```bash
docker compose down -v
```

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
* indexes for common ticket access patterns:

  * `user_id`
  * `status`
  * `category`
  * `created_at`

## Smoke Verification

After the Docker stack is running, verify the ticket API:

```bash
scripts/verify_ticket_api.sh
```

The script checks:

* health endpoint
* ticket creation
* ticket retrieval by id
* list filters
* pagination validation
* invalid query validation
* ticket update
* ticket deletion

The script defaults to:

```text
http://localhost:8001
```

To test another base URL:

```bash
BASE_URL=http://localhost:8000 scripts/verify_ticket_api.sh
```

## Example Ticket Creation

```bash
curl -X POST http://localhost:8001/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "Login issue",
    "description": "User cannot log in",
    "status": "open",
    "priority": "high",
    "category": "auth",
    "tags": ["login", "auth"]
  }'
```

## Configuration

The main environment variable is:

```text
DATABASE_URL
```

Docker Compose uses:

```text
postgresql+psycopg://ticket_user:ticket_password@postgres:5432/ticket_db
```

Application metadata can also be configured through:

```text
APP_NAME
ENVIRONMENT
```

## Docker Build Notes

The Docker image uses official PyPI by default:

```text
https://pypi.org/simple
```

The package index is configurable through the Docker build argument:

```text
PIP_INDEX_URL
```

Dependency download retry behavior is intentionally bounded so network failures fail in a reasonable time instead of hanging for several minutes.

## Project Direction

The next major step is adding Elasticsearch as a search projection while keeping PostgreSQL as the source of truth.

Planned work:

* Elasticsearch service in Docker Compose
* explicit ticket index mapping
* indexing tickets after create/update/delete
* search endpoint with full-text query and filters
* reindex script from PostgreSQL

