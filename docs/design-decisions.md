# Design Decisions

This document explains the main tradeoffs behind the current implementation.

## PostgreSQL Is the Source of Truth

Ticket data is stored durably in PostgreSQL. Elasticsearch is used only as a search projection.

Why:

- ticket writes should not depend on Elasticsearch availability
- relational data, migrations, constraints, and transactions fit the ticket domain well
- the search index can be deleted and rebuilt without losing business data

Tradeoff:

- search results can become temporarily stale if projection sync is delayed

Mitigation:

- ticket writes create durable outbox events in the same transaction
- failed projection sync keeps retry metadata
- the full index can be rebuilt from PostgreSQL

## Elasticsearch Is a Projection, Not a Database

The project uses Elasticsearch for full-text search, tag filtering, date ranges, and search-oriented sorting.

Why:

- full-text search and filter-heavy access are better served by a search engine than by ad hoc SQL queries
- explicit mappings make field behavior predictable
- search query construction can be tested separately from HTTP routes

Tradeoff:

- the system now has two data stores to keep consistent

Mitigation:

- PostgreSQL remains authoritative
- outbox sync and reindexing make the projection recoverable

## Outbox Instead of Direct Indexing in the Request

Ticket writes do not directly rely on Elasticsearch as part of the request lifecycle.

Why:

- a ticket write should still succeed if Elasticsearch is temporarily down
- the intent to update search is stored durably
- failures become visible through outbox status, retry count, and last error

Tradeoff:

- search may lag behind the latest write
- a processor is needed to drain the outbox

Mitigation:

- outbox rows include retry scheduling metadata
- the next phase can wire the existing processor as a dedicated worker service

## Explicit Mapping Instead of Dynamic Mapping

The ticket index uses an explicit `tickets_v1` mapping.

Why:

- `text` fields and `keyword` fields need different behavior
- exact filters should not depend on dynamic mapping guesses
- strict mappings catch unexpected document shapes early

Tradeoff:

- mapping changes need deliberate migration or reindexing

Mitigation:

- the index name is versioned
- the reindex command rebuilds documents from PostgreSQL

## Query Builder Outside the API Route

Elasticsearch query construction lives in `app/search/queries.py`.

Why:

- route handlers stay focused on HTTP concerns
- search behavior can be unit tested without a live Elasticsearch instance
- query rules are easier to evolve without changing request handling

Tradeoff:

- one more small layer exists between the route and Elasticsearch

Mitigation:

- the layer is intentionally narrow and covered by focused tests

## Separate Basic Health and Search Health

The API exposes `/health` and `/health/search` separately.

Why:

- an Elasticsearch outage should not always mean the API process is down
- operators need to distinguish API liveness from search readiness
- search-specific failures are easier to diagnose

Tradeoff:

- clients must know which health endpoint matches their use case

Mitigation:

- the README and operations docs define the meaning of each endpoint

## Structured Logs with Event Names

Operational logs use JSON formatting and stable `event` names.

Why:

- request id propagation makes request-level debugging easier
- stable event names make logs searchable
- ticket, outbox, search, and reindex behavior can be inspected without a debugger

Tradeoff:

- structured logging adds a small amount of setup code

Mitigation:

- logging setup is centralized in `app/core/logging.py`
- tests cover request id and extra field formatting

## Current Runtime Boundary

The code includes an outbox processor component, but Docker Compose does not yet run it as a continuous worker service.

Why:

- the project first proves the data model, processor behavior, retries, reindexing, search API, and observability
- worker runtime behavior is a separate operational concern

Tradeoff:

- local end-to-end sync currently depends on explicitly running setup/reindex or processor-related flows

Mitigation:

- the next practical phase is to add a worker entrypoint and Compose worker service

