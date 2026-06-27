# Operations Notes

This document collects the commands used most often during local development and verification.

## Local Python

Create a virtual environment:

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

Run the API:

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest -q
```

## Docker Compose

Build and start the full stack:

```bash
docker compose up --build -d
```

View containers:

```bash
docker compose ps -a
```

Follow API logs:

```bash
docker compose logs -f api
```

Stop the stack:

```bash
docker compose down
```

Remove local PostgreSQL and Elasticsearch volumes:

```bash
docker compose down -v
```

## Elasticsearch Index

Create the configured ticket index:

```bash
python -m app.search.setup
```

Inside Docker Compose:

```bash
docker compose exec api python -m app.search.setup
```

Rebuild the Elasticsearch projection from PostgreSQL:

```bash
python -m app.search.reindex
```

Inside Docker Compose:

```bash
docker compose exec api python -m app.search.reindex
```

## Health Checks

Basic API health:

```bash
curl http://localhost:8001/health
```

Search subsystem health:

```bash
curl http://localhost:8001/health/search
```

Expected search health meanings:

| Status | Meaning |
| --- | --- |
| `ok` | Elasticsearch is reachable and the ticket index exists |
| `degraded` | Elasticsearch is reachable but the ticket index is missing |
| `unavailable` | Elasticsearch could not be reached or did not pass ping |

## Smoke Verification

After the stack is running, run:

```bash
scripts/verify_search_flow.sh
```

The default API base URL is:

```text
http://localhost:8001
```

Override it when needed:

```bash
BASE_URL=http://localhost:8000 scripts/verify_search_flow.sh
```

The smoke script verifies the create-to-search path at a higher level than the unit tests:

- wait for the API health endpoint
- ensure the Elasticsearch ticket index exists
- create a ticket through the API
- search for that ticket through the Elasticsearch-backed endpoint
- delete the smoke-test ticket

## Logs

Logs are formatted as JSON and include structured fields such as:

- `event`
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`
- `ticket_id`
- `outbox_event_id`

When debugging a request, start with the response `X-Request-ID` and search for the same `request_id` in logs.

## Common Local Fixes

| Symptom | Likely cause | Command |
| --- | --- | --- |
| `/health` works but `/health/search` returns `degraded` | Ticket index is missing | `docker compose exec api python -m app.search.setup` |
| Search endpoint returns no newly created tickets | Projection has not been synced | `docker compose exec api python -m app.search.reindex` |
| Local data is confusing or stale | Docker volumes contain old state | `docker compose down -v` |
| API is not reachable on port `8000` | Docker exposes the API on `8001` | Use `http://localhost:8001` |
