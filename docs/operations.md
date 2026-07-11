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

Run one local outbox-processing batch:

```bash
python -m app.outbox.cli
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

The Compose stack includes:

- PostgreSQL
- Alembic migration container
- Redis
- Elasticsearch
- API
- Celery worker
- Celery beat scheduler

The API, worker, and beat use the application image's non-root `app` user.
Verify their runtime identities with:

```bash
docker compose exec api whoami
docker compose exec worker whoami
docker compose exec beat whoami
```

Each command should print:

```text
app
```

Follow API logs:

```bash
docker compose logs -f api
```

Follow worker and beat logs:

```bash
docker compose logs -f worker
docker compose logs -f beat
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

PostgreSQL remains the durable source of truth. Reindexing recreates the
eventually consistent Elasticsearch projection from current ticket rows.

## Local Demo Identity Headers

All `/tickets` endpoints require `X-User-ID`. The optional `X-User-Role`
defaults to `user` and accepts `user` or `admin`. These headers provide local
demo authentication context for exercising authorization; their values are not
cryptographically verified and are not production identity verification.

Create a ticket as a regular user. The payload owner must equal the header:

```bash
curl -X POST "http://localhost:8001/tickets" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 42" \
  -d '{
    "user_id": 42,
    "title": "Payment failed",
    "description": "Customer payment failed during checkout.",
    "status": "open",
    "priority": "high",
    "category": "billing",
    "tags": ["payment", "checkout"]
  }'
```

List or search as that regular user:

```bash
curl "http://localhost:8001/tickets?limit=20&offset=0" \
  -H "X-User-ID: 42"

curl "http://localhost:8001/tickets/search?q=payment&limit=20&offset=0" \
  -H "X-User-ID: 42"
```

An admin can list or search across users by omitting the `user_id` filter:

```bash
curl "http://localhost:8001/tickets?limit=20&offset=0" \
  -H "X-User-ID: 1" \
  -H "X-User-Role: admin"

curl "http://localhost:8001/tickets/search?q=payment&limit=20&offset=0" \
  -H "X-User-ID: 1" \
  -H "X-User-Role: admin"
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
| HTTP `200`, body status `ok` | Elasticsearch responded successfully to the ping check |
| HTTP `503`, body status `unavailable` | Elasticsearch ping failed, returned false, or raised an exception |

`/health` is an API liveness check. `/health/search` checks Elasticsearch
reachability; the current implementation does not separately verify ticket
index existence. These endpoints do not replace full deployment readiness or
dependency monitoring.

## Metrics

Read the Prometheus-compatible endpoint:

```bash
curl http://localhost:8001/metrics
```

The application exposes these metric families:

- `http_requests_total`
- `http_request_duration_seconds`
- `search_requests_total`
- `search_unavailable_total`
- `search_request_duration_seconds`
- `outbox_events_by_status`

The endpoint can be scraped by a Prometheus server, but this repository does
not start Prometheus, Alertmanager, or Grafana.

Operationally, watch HTTP request rate and error statuses, API latency, search
latency, search-unavailable growth, and the `pending`, `processing`, and
`failed` outbox gauges. A growing pending backlog can indicate a worker, beat,
Elasticsearch, or retry problem; old processing work can indicate stuck events;
failed events require review of worker logs and retry state.

Recommended future alerts, not alerts implemented by this repository, include:

- sustained growth in search-unavailable events
- a growing pending outbox backlog
- events remaining in processing past the configured timeout
- failed outbox events
- elevated HTTP or search latency

## Smoke Verification

After the stack is running, run:

```bash
scripts/verify_search_flow.sh
```

The script currently verifies:

1. API readiness.
2. The `app` runtime user for the API, worker, and beat.
3. `/metrics` availability and the HTTP/outbox metric families used by the
   smoke flow.
4. Elasticsearch readiness and ticket-index setup.
5. `/health/search`.
6. Authenticated ticket creation with matching header and payload ownership.
7. Processing of the corresponding `ticket.created` outbox event.
8. Authenticated Elasticsearch search for the created ticket.
9. Exposure of search request and duration metrics.

On failure it prints Docker Compose state and recent logs for the API,
migration, PostgreSQL, Elasticsearch, worker, and beat services.

The default API base URL is:

```text
http://localhost:8001
```

Override it when needed:

```bash
BASE_URL=http://localhost:8000 scripts/verify_search_flow.sh
```

## Logs

The API process configures JSON logs. Logs emitted during an HTTP request
include the active `request_id`; incoming `X-Request-ID` is reused and otherwise
the API generates one. Celery manages the worker and beat output format, so
their console logs should not be assumed to use the API JSON formatter.

Application logging calls attach fields such as:

- `event`
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`
- `ticket_id`
- `outbox_event_id`
- `claimed_count`
- `processed`
- `failed`

Whether a field appears in worker or beat console output depends on Celery's
formatter. When debugging an API request, start with the response
`X-Request-ID` and search API logs for the same `request_id`.

## Common Local Fixes

| Symptom | Likely cause | Command |
| --- | --- | --- |
| Protected endpoint returns `401` | `X-User-ID` is missing/invalid or `X-User-Role` is invalid | Supply valid local demo headers |
| Request returns `403` | A regular user explicitly requested another user's ownership scope | Use the current user's scope or an authorized admin context |
| Direct ticket access returns `404` | The ticket is missing or hidden by ownership | Confirm the ticket ID and current-user context |
| `/health` works but `/health/search` returns `503` | Elasticsearch ping failed | Check `docker compose logs --tail=120 elasticsearch` |
| `/metrics` fails | The API or its PostgreSQL dependency is unavailable | Check API and PostgreSQL container state and logs |
| Outbox pending grows | Worker, beat, Elasticsearch, or retry processing is unhealthy | Check worker, beat, and Elasticsearch logs |
| Worker runs as root | The application image is stale or was built incorrectly | Rebuild with `docker compose up --build -d` |
| Search does not show a newly created ticket yet | Eventual consistency; the outbox event has not been processed | Check `docker compose logs -f worker` |
| Search projection looks stale | Elasticsearch projection is behind PostgreSQL | `docker compose exec api python -m app.search.reindex` |
| Local data is confusing or stale | Docker volumes contain old PostgreSQL or Elasticsearch state | `docker compose down -v` |
| API is not reachable on port `8000` | Docker exposes the API on `8001` | Use `http://localhost:8001` |

Useful diagnostics:

```bash
docker compose ps -a
docker compose logs --tail=120 api
docker compose logs --tail=120 worker
docker compose logs --tail=120 beat
docker compose logs --tail=120 elasticsearch
docker compose logs --tail=120 migrate
```

If Elasticsearch is reachable but the ticket index is absent, create it with:

```bash
docker compose exec api python -m app.search.setup
```

## Security and Production Boundaries

A real deployment must replace the local identity headers with trusted,
verifiable identity while preserving the existing ownership authorization
boundary. Future deployment concerns include JWT/OIDC or trusted-gateway
identity, TLS, secrets management, network boundaries, rate limiting, a
Prometheus deployment and scrape configuration, alerting, and Grafana
dashboards. None of these production identity or monitoring-platform
components is implemented by the current repository.
