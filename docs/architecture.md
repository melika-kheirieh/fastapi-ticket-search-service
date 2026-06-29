# Architecture Notes

This service is built around one boundary:

**PostgreSQL owns durable ticket state. Elasticsearch owns the search projection.**

The API never treats Elasticsearch as the system of record. Search can be temporarily stale, unavailable, or rebuilt without losing ticket data.

## Runtime Boundaries

| Boundary | Responsibility |
| --- | --- |
| FastAPI routes | HTTP validation, dependency wiring, response models |
| Service layer | Ticket use cases and transaction-level orchestration |
| Repositories | PostgreSQL reads and writes |
| PostgreSQL | Durable ticket data and durable outbox events |
| Redis | Celery broker and result backend for scheduled outbox processing |
| Celery beat | Schedules periodic outbox-processing tasks |
| Celery worker | Runs outbox-processing tasks |
| Outbox processor | Converts ticket events into Elasticsearch index/delete operations |
| Elasticsearch | Full-text and filter-heavy search projection |
| Reindex command | Rebuilds Elasticsearch from PostgreSQL |

## Write Path

Ticket writes and outbox events are committed together.

```mermaid
flowchart TD
    A["POST/PATCH/DELETE /tickets"] --> B["TicketService"]
    B --> C["TicketRepository"]
    B --> D["OutboxEventRepository"]
    C --> E["tickets table"]
    D --> F["outbox_events table"]
```

This means the application does not need Elasticsearch to be healthy in order to accept ticket writes.

## Incremental Search Sync

Celery beat schedules outbox-processing batches, and the Celery worker runs them after the write transaction exists in PostgreSQL.

```mermaid
flowchart TD
    A["Celery beat"] --> B["process_outbox_batch task"]
    B --> C["Celery worker"]
    C --> D["Claim ready events"]
    D --> E["Index or delete document"]
    E --> F["Mark processed"]
    E --> G["Mark failed with retry metadata"]
```

The processor stores retry state in PostgreSQL:

- `status`
- `retry_count`
- `last_error`
- `next_attempt_at`
- `processed_at`

That keeps failure handling visible and testable.

## Full Rebuild

The reindex command is the recovery path for a missing or stale search projection.

```mermaid
flowchart TD
    A["PostgreSQL tickets"] --> B["python -m app.search.reindex"]
    B --> C["tickets_v1 index"]
```

Reindexing is useful when:

- the Elasticsearch index is recreated
- the mapping changes
- local development data is reset
- projection state is suspected to be stale

## Search Path

Search requests use a dedicated query builder before touching Elasticsearch.

```mermaid
flowchart TD
    A["GET /tickets/search"] --> B["Validated query params"]
    B --> C["build_ticket_search_query"]
    C --> D["Elasticsearch search"]
    D --> E["TicketResponse list"]
```

Keeping query construction outside the route makes the behavior easy to unit test without a live Elasticsearch service.

## Health Model

The API exposes two health endpoints with different meanings:

| Endpoint | Meaning |
| --- | --- |
| `/health` | The API process is alive |
| `/health/search` | Elasticsearch is reachable and the configured ticket index exists |

This separation prevents a search outage from being confused with a total API outage.

## Failure and Recovery Model

| Failure | Expected behavior | Recovery path |
| --- | --- | --- |
| Elasticsearch is down during a ticket write | The PostgreSQL write can still succeed | The outbox event remains durable and can be retried |
| Outbox processing fails | The event is marked `failed` with retry metadata | Retry after `next_attempt_at` until the retry limit is reached |
| Elasticsearch index is missing | `/health/search` reports a degraded state | Run `python -m app.search.setup` |
| Search projection is stale or corrupted | PostgreSQL remains authoritative | Run `python -m app.search.reindex` |
| API is alive but search is unavailable | `/health` and `/health/search` report different states | Diagnose the search dependency without masking API liveness |

## Consistency Model

Ticket writes are strongly consistent inside PostgreSQL: the ticket row and outbox event are committed in the same transaction.

Search is eventually consistent: Elasticsearch can lag behind PostgreSQL until the worker processes ready outbox events, or until a full reindex rebuilds the projection.

That tradeoff is intentional. It keeps ticket writes independent from Elasticsearch availability while still preserving the intent to update search.