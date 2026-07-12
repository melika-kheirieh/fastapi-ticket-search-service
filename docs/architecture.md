# Architecture Notes

This service is built around one boundary:

**PostgreSQL is the durable source of truth. Elasticsearch hosts an eventually
consistent, rebuildable search projection.**

The API never treats Elasticsearch as the system of record. Search can be temporarily stale, unavailable, or rebuilt without losing ticket data.

## Runtime Boundaries

| Boundary | Responsibility |
| --- | --- |
| FastAPI routes | Validate HTTP input, wire dependencies, enforce route-level access boundaries, and serialize responses |
| Authentication dependency | Validates demo identity headers and constructs a `CurrentUser` |
| Authorization helpers/boundary | Resolves visible ownership scope and hides inaccessible individual resources |
| Service layer | Runs ticket use cases and transaction-level write orchestration after authorization |
| Repositories | Encapsulate PostgreSQL ticket and outbox reads and writes |
| PostgreSQL | Durable source of truth for ticket state and outbox intent |
| Redis | Celery broker and result backend |
| Celery beat | Schedules periodic outbox-processing tasks |
| Celery worker | Executes scheduled outbox-processing tasks |
| Outbox processor | Claims ready events, updates Elasticsearch, and stores processing or retry state |
| Elasticsearch | Eventually consistent, rebuildable full-text search projection |
| Metrics instrumentation | Records HTTP and search counters/histograms and maintains outbox gauges |
| `/metrics` | Reads current outbox counts and exposes the Prometheus client registry |
| Reindex command | Recreates and rebuilds the Elasticsearch projection from PostgreSQL |

## Authentication Context

Every `/tickets` route depends on `get_current_user`. The dependency reads
`X-User-ID` and the optional `X-User-Role`, validates both values, defaults the
role to `user`, and creates a `CurrentUser`. The identifier must be a positive
integer, and the role must be either `user` or `admin`. Missing or invalid
context returns `401` before the ticket domain service runs.

This header mechanism provides demo authentication context so the repository
can exercise authorization behavior. The supplied values are not
cryptographically verified and are not production identity verification. JWT,
OAuth/OIDC, login, password handling, and production identity-provider
integration are not implemented.

## Authorization Model

Regular users are restricted to tickets whose `user_id` matches their current
user ID. Admins can access tickets across users.

- Create validates payload ownership before calling the ticket service.
- List resolves a regular user's ownership filter before querying PostgreSQL.
- Search resolves ownership before constructing the Elasticsearch query.
- Get, update, and delete load the resource and apply an ownership check before
  returning or mutating it.
- Admin list and search can target one `user_id` or omit it to span users.

| Status | Meaning |
| ------ | ------- |
| `401` | Authentication context is missing or invalid |
| `403` | The authenticated user explicitly requests a forbidden ownership scope |
| `404` | A resource belonging to another user is hidden |

## Write Path

Authorization is checked in the route boundary before a mutation reaches the
ticket service. The service then commits the ticket change and its outbox event
together in one PostgreSQL transaction.

```mermaid
flowchart TD
    A["POST/PATCH/DELETE /tickets"] --> B["Authentication and authorization"]
    B --> C["TicketService"]
    C --> D["TicketRepository"]
    C --> E["OutboxEventRepository"]
    D --> F["tickets table"]
    E --> G["outbox_events table"]
```

Elasticsearch does not participate in this transaction. The application does
not need Elasticsearch to be healthy in order to accept ticket writes.

## Transactional Outbox Consistency

Ticket state and outbox intent are transactionally consistent inside
PostgreSQL: the ticket row change and outbox event (`ticket.created`,
`ticket.updated`, or `ticket.deleted`) are committed in the same transaction.

If Elasticsearch is down during a write, the PostgreSQL commit can still
succeed. The durable outbox event retains the intent to update search. Search
itself remains eventually consistent until a worker processes ready events or a
full reindex rebuilds the projection.

## Celery and Redis Processing Path

Celery beat schedules outbox-processing batches through Redis. The Celery
worker claims ready events from PostgreSQL and indexes or deletes documents in
Elasticsearch.

```mermaid
flowchart TD
    A["Celery beat"] --> B["process_outbox_batch task"]
    B --> C["Celery worker"]
    C --> D["Claim ready events"]
    D --> E["Index or delete document"]
    E --> F["Mark processed"]
    E --> G["Mark failed with retry metadata"]
```

Redis is the Celery broker and result backend. The Docker Compose beat schedule
is currently fixed at 10 seconds.

## Retry and Stuck-Event Recovery

The processor stores retry state in PostgreSQL:

- `status`
- `retry_count`
- `last_error`
- `next_attempt_at`
- `processed_at`

It claims:

- `pending` events
- `failed` events whose `next_attempt_at` has arrived and whose `retry_count`
  remains below the configured limit
- `processing` events older than the configured timeout whose `retry_count`
  also remains below the limit

Row locking with `SKIP LOCKED` avoids duplicate claims across workers.
Timeout-based reclamation recovers work left stuck by an interrupted processor.
Failed events retain visible retry metadata until they are processed or exhaust
the retry limit.

## Elasticsearch Search Projection

Elasticsearch stores a rebuildable projection of ticket documents for
full-text search and filter queries. It is not the system of record.

- Index mapping and settings: [`app/search/mappings.py`](../app/search/mappings.py)
- Query construction (`multi_match`, filters, pagination, sort):
  [`app/search/queries.py`](../app/search/queries.py)

The default index name is `tickets_v1`. Create a missing index with
`python -m app.search.setup`. Rebuild from PostgreSQL with
`python -m app.search.reindex`.

## Search Authorization Boundary

Elasticsearch is a separate projection and must not bypass authorization. The
route resolves the visible `user_id` before query construction: every
regular-user query includes the current user's identifier, while an admin query
may target one user or span users. A regular user who explicitly asks for a
different `user_id` receives `403` before Elasticsearch is called.

```mermaid
flowchart TD
    A["Search request"] --> B["Authentication dependency"]
    B --> C["CurrentUser"]
    C --> D["Resolve visible user_id"]
    D --> E["Build Elasticsearch query"]
    E --> F["Elasticsearch projection"]
    F --> G["Authorized results"]
```

Authorization is therefore not only a post-filter after results return.
Including ownership in the Elasticsearch query reduces unauthorized exposure
at the search data-access boundary. The dedicated query builder also keeps this
behavior unit-testable without a live Elasticsearch service.

## Reindex Recovery

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

## Metrics and Health Architecture

HTTP middleware records request counters and duration histograms. The search
route records success or unavailable outcomes and search duration around the
Elasticsearch call. On each `GET /metrics`, the application reads current
outbox status counts from PostgreSQL, updates gauges, and exposes the
Prometheus client registry.

```mermaid
flowchart LR
    A["HTTP middleware"] --> D["Prometheus client registry"]
    B["Search endpoint"] --> D
    C["PostgreSQL outbox counts"] --> D
    D --> E["GET /metrics"]
```

The application defines:

- `http_requests_total`
- `http_request_duration_seconds`
- `search_requests_total`
- `search_unavailable_total`
- `search_request_duration_seconds`
- `outbox_events_by_status`

For matched endpoints, HTTP labels use the method, route template, and status.
Query strings and identifiers such as request IDs, ticket IDs, and user IDs are
intentionally excluded from metric labels. Instrumentation sits outside the
PostgreSQL ticket/outbox transaction and does not make ticket writes or search
execution depend on a monitoring server.

The application has Prometheus-compatible instrumentation. This repository
does not deploy a Prometheus server, Alertmanager, or Grafana.

The API exposes two health endpoints with different meanings:

| Endpoint | Meaning |
| --- | --- |
| `/health` | The API process is alive |
| `/health/search` | Elasticsearch responds successfully to the application's ping check |

This separation prevents a search outage from being confused with a total API
outage. The current search health implementation checks reachability, not
ticket-index existence, and neither endpoint replaces broader deployment
readiness checks.

## Failure and Consistency Models

| Failure | Expected behavior | Recovery path |
| --- | --- | --- |
| Authentication context is missing | The request returns `401` and does not enter the domain service | Supply valid demo headers locally; use trusted identity verification in a real deployment |
| Authentication context is invalid | The request returns `401` and does not enter the domain service | Correct `X-User-ID` or `X-User-Role` |
| Regular user requests another user's list/search scope | The request returns `403` before the repository/search query | Request the current user's scope or use an authorized admin context |
| Regular user directly accesses another user's resource | The request returns ownership-hidden `404` | Use the resource owner's or an admin context |
| Elasticsearch is down during a ticket write | The PostgreSQL write can still succeed | The outbox event remains durable and can be retried |
| Outbox processing fails | The event is marked `failed` with retry metadata | Retry after `next_attempt_at` until the retry limit is reached |
| Elasticsearch index is missing | Search/index operations fail; the ping-based search health check may still be `ok` | Run `python -m app.search.setup` |
| Search projection is stale or corrupted | PostgreSQL remains authoritative | Run `python -m app.search.reindex` |
| API is alive but search is unavailable | `/health` and `/health/search` report different states | Diagnose the search dependency without masking API liveness |
| Metrics scraper or monitoring system is unavailable | Ticket writes and search continue because they do not call a monitoring server | Restore the external scraper or monitoring system |
| `/metrics` cannot query PostgreSQL | The scrape request fails; ticket data remains authoritative in PostgreSQL | Diagnose the API/database dependency |

Ticket state and outbox intent are transactionally consistent inside
PostgreSQL. Search is eventually consistent: Elasticsearch can lag behind
PostgreSQL until the worker processes ready outbox events, or until a full
reindex rebuilds the projection.

Authorization is still evaluated synchronously for every request, including
search requests. Eventual consistency does not weaken the ownership boundary.
The consistency tradeoff keeps ticket writes independent from Elasticsearch
availability while preserving the intent to update search.
