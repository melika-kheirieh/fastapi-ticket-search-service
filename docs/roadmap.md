# Roadmap

This roadmap keeps reliable persistence and projection first, the outbox runtime
and application observability next, measurable lexical search before semantic
or hybrid search, verifiable production authentication after the search
baseline, and final polish at the end.

The project is complete through **Phase 4** plus the current backend reliability
and authorization hardening milestone. This is not completion of the
lexical/semantic search phases, a production deployment, or a complete
authentication product.

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

- Request ID middleware
- `X-Request-ID` response header
- Structured JSON logging for the FastAPI process
- Operational events for request, ticket, search, and outbox behavior
- Reindex command output reporting the number of rebuilt ticket documents
- Prometheus-compatible HTTP and search counters/histograms
- PostgreSQL-backed outbox status gauges
- `/metrics`
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
- Configurable batch size, retry count, processing timeout, and Celery beat
  interval (`OUTBOX_BEAT_SCHEDULE_SECONDS`, default 10 seconds)
- Smoke verification for the API-to-worker-to-Elasticsearch path
- Unit tests for Celery schedule configuration and outbox task behavior

Outcome:

With Docker Compose, the API, Celery worker, and Celery beat run as separate processes. Creating a ticket through the API eventually makes it searchable without manually calling the processor.

Architecture summary:

"Ticket writes commit the ticket row and an outbox event in the same PostgreSQL transaction. A separate Celery worker claims ready outbox events and updates Elasticsearch. If Elasticsearch is down, the event stays in PostgreSQL with retry metadata, so the system does not lose the intent to update the search projection."

### Current Hardening Milestone: Authorization, Runtime, and Verification

Goal:

Harden the existing backend boundary and make its local runtime claims
repeatable without presenting demo identity as production authentication.

Completed work:

- Header-based current-user dependency using `X-User-ID` and optional
  `X-User-Role`
- `user` and `admin` role context
- Ownership authorization across create, list, get, update, delete, and search
- Search ownership resolved before Elasticsearch query construction
- Protection against cross-user search exposure
- Non-root `app` runtime for API, worker, and beat
- `.env.example`
- Hardened Docker smoke verification for runtime users, metrics, outbox
  processing, authenticated creation, and search
- GitHub Actions Docker smoke job
- Test-suite organization and coverage polish

Outcome:

The repository now demonstrates a backend reliability and authorization
hardening milestone. PostgreSQL remains the durable source of truth,
Elasticsearch remains an eventually consistent, rebuildable projection, and
authorization is enforced synchronously across both data paths.

## Future Phases

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

### Phase 7: Verifiable Production Authentication

Goal:

Replace the demo header-based identity mechanism with verifiable authentication
while preserving the existing ownership authorization boundary.

Planned work:

- Add a persistent `User` model and migrations if local account management is
  still desired
- Add password hashing and login if password-based identity is chosen
- Issue access tokens and add JWT validation
- Add refresh-token handling
- Integrate a production identity provider
- Validate trusted claims and support signing-key rotation
- Strengthen multi-tenant boundaries beyond the current ownership model
- Test invalid/expired credentials while retaining ownership, admin, and search
  boundary coverage

Acceptance criteria:

- Identity is verifiable rather than accepted directly from caller-supplied
  headers.
- JWT/OIDC or trusted-gateway claims feed the existing current-user and
  authorization boundary.
- Existing ownership and cross-user search protections remain intact.

### Phase 8: Deployment and Operational Hardening

Goal:

Prepare the service for deployment-oriented operational work without claiming that the repository is a complete production platform.

Planned work:

- Improve OpenAPI tags and descriptions where still relevant
- Check that no real secrets are committed
- Deploy and configure a Prometheus server when a monitoring environment exists
- Add scrape configuration and alert rules
- Add Alertmanager routing and Grafana dashboards if operationally justified
- Add distributed tracing/OpenTelemetry if needed

Acceptance criteria:

- Deployment-oriented operational concerns are addressed without overstating current scope.
- External monitoring and alerting can be added without changing the application boundary.
- Limitations remain honest about what the repository does not deploy.

## Intentionally Deferred

- Kubernetes deployment
- Kafka or a distributed event bus
- Complex multi-tenant authorization beyond the current ownership boundary
- A frontend dashboard
- Full production secrets management
- A full observability platform: Prometheus server, scrape configuration, alert
  rules, Alertmanager, Grafana, and optional distributed tracing/OpenTelemetry
- Semantic and hybrid search until a lexical evaluation baseline exists
- PostgreSQL full-text search and Persian analyzer support
- Production authentication (JWT/OIDC or trusted-gateway identity)

These can be useful later, but they are not implemented by the current
backend-search milestone. Prometheus-compatible application metrics are already
implemented; only the external monitoring platform remains deferred.
