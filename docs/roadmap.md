# Roadmap

This roadmap keeps backend reliability first, measurable lexical search next, semantic and hybrid search after that, auth boundaries later, and final production/documentation polish at the end.

The project is currently complete through **Phase 4**.

## Completed

### Phase 0: Repository Trust

Goal:

Make the repository reliable to run, review, and extend before adding more features.

Completed work:

- GitHub Actions CI
- README baseline
- Design summary around PostgreSQL as source of truth and Elasticsearch as projection
- Docker Compose verification path
- pytest suite
- Smoke script for the local search flow

Outcome:

The repository has a clear technical direction and a repeatable local verification path.

### Phase 1: Search API Behavior

Goal:

Make the search endpoint predictable beyond the happy path.

Completed work:

- Clean Elasticsearch client dependency boundary
- Search unavailable behavior with `503`
- Query builder separated from API routing
- Validation and filter coverage
- Clear distinction between `/tickets` database filtering and `/tickets/search` Elasticsearch search

Outcome:

The search API is testable, explainable, and failure-aware.

### Phase 2: Reliability and Sync

Goal:

Make ticket-to-Elasticsearch synchronization durable when Elasticsearch fails.

Completed work:

- `outbox_events` table
- Transactional outbox event creation for `ticket.created`, `ticket.updated`, and `ticket.deleted`
- `OutboxProcessor`
- Event statuses for pending, processing, processed, and failed states
- Retry metadata with `retry_count`, `last_error`, `processed_at`, and `next_attempt_at`
- Stuck processing recovery
- Reindex flow to rebuild Elasticsearch from PostgreSQL
- Tests for outbox writes, retry behavior, failure handling, and reindexing

Outcome:

Elasticsearch is no longer a fragile best-effort side effect. It is a rebuildable projection with durable sync intent.

### Phase 3: Observability

Goal:

Make search and outbox failures diagnosable.

Completed work:

- Request id middleware
- `X-Request-ID` response header
- Structured JSON logging
- Operational events for request, ticket, search, outbox, worker, and reindex behavior
- `/health/search` endpoint
- Smoke script documentation

Outcome:

The project is easier to debug and easier to discuss in operational terms.

### Phase 4: Runtime Reliability and Celery-Backed Outbox Processing

Goal:

Move the outbox processor from a tested component to a real runtime path.

Completed work:

- One-shot outbox CLI through `app.outbox.cli`
- Celery task for scheduled outbox batch processing
- Celery worker and beat services in Docker Compose
- Redis service for Celery broker/result backend
- Configurable batch size, retry count, processing timeout, and beat schedule
- Smoke verification for the API-to-worker-to-Elasticsearch path
- Unit tests for Celery schedule configuration and outbox task behavior

Outcome:

With Docker Compose, the API, Celery worker, and Celery beat run as separate processes. Creating a ticket through the API eventually makes it searchable without manually calling the processor.

Architecture summary:

"Ticket writes commit the ticket row and an outbox event in the same PostgreSQL transaction. A separate Celery worker claims ready outbox events and updates Elasticsearch. If Elasticsearch is down, the event stays in PostgreSQL with retry metadata, so the system does not lose the intent to update the search projection."

## Next Steps

### Phase 5: Lexical Search Maturity, PostgreSQL FTS, Persian Analyzer, and Eval

Goal:

Build a measurable lexical search baseline before adding embeddings.

Planned work:

- Add PostgreSQL full-text search for `title` and `description`
- Add a comparison path for database FTS versus Elasticsearch search
- Add migration/index support where needed
- Create a new Elasticsearch index version, for example `tickets_v2`
- Add Persian/custom analyzer support
- Add Persian and English sample tickets
- Build a small golden dataset of search queries
- Calculate metrics such as `precision@5`, `recall@5`, `hit_rate@5`, and `MRR`
- Compare PostgreSQL FTS, Elasticsearch default search, and Elasticsearch Persian analyzer behavior

Acceptance criteria:

- Search quality is measured instead of judged only by manual inspection.
- Persian and mixed-language search have a demo path.
- README or docs include a short evaluation summary.

### Phase 6: Embedding, Semantic Search, Hybrid Search, and Eval

Goal:

Add embedding-backed search in a way that is testable and benchmarked against the lexical baseline.

Planned work:

- Add an `EmbeddingProvider` interface
- Add a deterministic fake embedding provider for tests
- Choose a multilingual embedding model suitable for Persian and English
- Add a vector field to the Elasticsearch mapping
- Generate embeddings from `title`, `description`, `category`, and `tags`
- Include embeddings in reindexing
- Include embeddings in outbox sync
- Add `lexical`, `semantic`, and `hybrid` search modes
- Implement a simple hybrid fusion strategy such as weighted scoring or RRF
- Run evaluation across all search modes
- Document tradeoffs and results

Acceptance criteria:

- Semantic and hybrid search work end to end.
- Evaluation shows how hybrid search changes quality compared with the lexical baseline.
- Embedding behavior is covered through the provider boundary and tests.

### Phase 7: Meaningful JWT and API Boundaries

Goal:

Make authentication affect domain behavior and search data access, instead of only decoding tokens.

Planned work:

- Add a `User` model
- Add user migrations
- Add password hashing
- Add login endpoint and access token
- Add current-user dependency
- Add simple `user` and `admin` roles
- Let normal users access only their own tickets
- Let admins access all tickets
- Apply authorization to list, get, create, update, delete, and search
- Prevent search data leaks across ownership boundaries
- Test login, invalid tokens, ownership, admin access, and search boundaries

Acceptance criteria:

- JWT changes what the user is allowed to see and mutate.
- Search respects ownership.
- A user cannot discover another user's tickets through search.

### Phase 8: Production Polish and Public Documentation Cleanup

Goal:

Prepare the repository for public review, local demos, and technical walkthroughs without claiming it is a full production platform.

Planned work:

- Add `.env.example`
- Document all environment variables
- Final README pass with architecture, demo path, features, limitations, and tradeoffs
- Add focused docs for architecture, operations, API examples, and roadmap
- Improve OpenAPI tags and descriptions
- Document major error cases for `401`, `403`, `404`, `422`, and `503`
- Add production boundaries and honest limitations
- Check that no real secrets are committed
- Improve Docker Compose docs
- Optionally add Docker smoke verification in CI if it stays stable

Acceptance criteria:

- GitHub explains the project without extra context.
- The demo path is obvious.
- Limitations are honest.
- The project is ready to share without requiring extra context.

## Intentionally Deferred

- Kubernetes deployment
- Kafka or a distributed event bus
- Complex multi-tenant authorization beyond the planned JWT boundary
- A frontend dashboard
- Full production secrets management
- Heavy observability stacks such as OpenTelemetry, Prometheus, or Grafana

These can be useful later, but they are not necessary for the current backend-search scope.