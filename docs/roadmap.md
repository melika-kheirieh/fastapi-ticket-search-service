# Roadmap

This roadmap is intentionally backend-focused. The goal is to keep the project useful as a portfolio piece without turning it into a vague platform.

## Completed

### Phase 1: Core Ticket API

- FastAPI application
- Ticket create/read/update/delete endpoints
- Pydantic request and response schemas
- SQLAlchemy ticket model
- Repository and service layers
- PostgreSQL persistence
- Alembic migrations
- Database filters and pagination
- Docker Compose stack
- GitHub Actions CI

### Phase 2: Search Projection

- Elasticsearch service in Docker Compose
- Elasticsearch client helper
- Explicit `tickets_v1` mapping
- Index setup command
- Ticket search document conversion
- Outbox events for ticket create/update/delete
- Retryable outbox processor component
- Full reindex command
- Query builder for text search, exact filters, date ranges, pagination, and sorting
- Search endpoint backed by Elasticsearch
- Tests for mapping, indexing, reindexing, query construction, and API forwarding

### Phase 3: Observability and Verification

- Request id middleware
- `X-Request-ID` response header
- Structured JSON logging
- Operational event names for request, ticket, outbox, search, and reindex behavior
- `/health/search` endpoint
- Docker-based smoke verification script

## Next Practical Steps

### Phase 4: Worker and Runtime Hardening

Goal: turn the existing outbox processor component into a real runtime process that can run beside the API.

- Add a dedicated outbox worker entrypoint
- Add a Docker Compose worker service
- Add graceful shutdown behavior for long-running processing
- Add worker logs and basic worker health visibility
- Add a focused integration test for the worker path if runtime cost stays reasonable

### Phase 5: Authentication and API Boundaries

Goal: make the API boundary more realistic without hiding the backend/search focus of the project.

- Add API key or JWT-based authentication
- Add route protection for ticket writes
- Add tests for authenticated and unauthenticated requests
- Document local auth setup clearly

### Phase 6: Search Quality

Goal: improve search relevance and user-facing search behavior after the consistency and runtime story is stable.

- Add search result highlighting
- Add analyzer experiments for Persian or mixed-language text
- Add sorting options
- Add richer search examples
- Consider suggestions or typo-tolerance after the baseline is stable

## Intentionally Deferred

- Kubernetes deployment
- Kafka or a distributed event bus
- Complex multi-tenant authorization
- AI/embedding search
- A frontend dashboard

Those can be good future extensions, but they are not necessary for the current backend-search portfolio goal.
