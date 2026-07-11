#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://localhost:9200}"
API_READY_TIMEOUT_SECONDS="${API_READY_TIMEOUT_SECONDS:-120}"
ELASTICSEARCH_READY_TIMEOUT_SECONDS="${ELASTICSEARCH_READY_TIMEOUT_SECONDS:-120}"
OUTBOX_READY_TIMEOUT_SECONDS="${OUTBOX_READY_TIMEOUT_SECONDS:-60}"
SMOKE_USER_ID="${SMOKE_USER_ID:-9001}"
MARKER="smoke-$(date +%s)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

show_docker_diagnostics() {
  echo
  echo "Docker Compose services:"
  docker compose ps -a || true

  echo
  echo "Recent api logs:"
  docker compose logs --no-color --tail=120 api || true

  echo
  echo "Recent migrate logs:"
  docker compose logs --no-color --tail=120 migrate || true

  echo
  echo "Recent postgres logs:"
  docker compose logs --no-color --tail=80 postgres || true

  echo
  echo "Recent elasticsearch logs:"
  docker compose logs --no-color --tail=120 elasticsearch || true

  echo
  echo "Recent worker logs:"
  docker compose logs --no-color --tail=120 worker || true

  echo
  echo "Recent beat logs:"
  docker compose logs --no-color --tail=120 beat || true
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local elapsed=0

  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    if curl -fsS "$url" >/dev/null; then
      return 0
    fi

    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "$name did not become ready at $url after ${timeout_seconds}s" >&2
  show_docker_diagnostics
  exit 1
}

assert_metrics_contains() {
  local metric_name="$1"

  if ! curl -fsS "$BASE_URL/metrics" | grep -q "$metric_name"; then
    echo "Metrics endpoint does not expose expected metric: $metric_name" >&2
    show_docker_diagnostics
    exit 1
  fi
}

verify_compose_service_user() {
  local service="$1"
  local expected_user="app"
  local actual_user

  actual_user="$(docker compose exec -T "$service" whoami | tr -d '[:space:]')"

  if [ "$actual_user" != "$expected_user" ]; then
    echo "Service $service is not running as expected user" >&2
    echo "Expected: $expected_user" >&2
    echo "Actual: $actual_user" >&2
    show_docker_diagnostics
    exit 1
  fi

  echo "Service $service is running as user $expected_user"
}

wait_for_outbox_processed() {
  local ticket_id="$1"
  local elapsed=0
  local status=""

  echo "Waiting for outbox event to be processed for ticket id $ticket_id"

  while [ "$elapsed" -lt "$OUTBOX_READY_TIMEOUT_SECONDS" ]; do
    status="$(
      docker compose exec -T postgres psql \
        -U ticket_user \
        -d ticket_db \
        -tAc "select status from outbox_events where aggregate_type = 'ticket' and aggregate_id = ${ticket_id} and event_type = 'ticket.created' order by id desc limit 1;"
    )"

    if [ "$status" = "processed" ]; then
      echo "Outbox event processed for ticket id $ticket_id"
      return 0
    fi

    if [ "$status" = "failed" ]; then
      echo "Outbox event failed for ticket id $ticket_id" >&2
      show_docker_diagnostics
      exit 1
    fi

    sleep 1
    elapsed=$((elapsed + 1))
  done

  echo "Outbox event for ticket id $ticket_id did not become processed; last status: ${status:-missing}" >&2
  show_docker_diagnostics
  exit 1
}

require_command curl
require_command docker
require_command python3
require_command grep

echo "Checking API health at $BASE_URL"
wait_for_http "API" "$BASE_URL/health" "$API_READY_TIMEOUT_SECONDS"

echo "Verifying runtime user for api service"
verify_compose_service_user "api"

echo "Verifying runtime user for worker service"
verify_compose_service_user "worker"

echo "Verifying runtime user for beat service"
verify_compose_service_user "beat"

echo "Checking metrics endpoint at $BASE_URL/metrics"
wait_for_http "Metrics endpoint" "$BASE_URL/metrics" "$API_READY_TIMEOUT_SECONDS"

echo "Checking HTTP metrics output"
assert_metrics_contains "http_requests_total"
assert_metrics_contains "http_request_duration_seconds"

echo "Checking outbox metrics output"
assert_metrics_contains "outbox_events_by_status"

echo "Checking Elasticsearch health at $ELASTICSEARCH_URL"
wait_for_http "Elasticsearch" "$ELASTICSEARCH_URL" "$ELASTICSEARCH_READY_TIMEOUT_SECONDS"

echo "Ensuring Elasticsearch index exists"
docker compose exec -T api python -m app.search.setup >/dev/null

echo "Checking search subsystem health at $BASE_URL/health/search"
wait_for_http "Search subsystem" "$BASE_URL/health/search" "$API_READY_TIMEOUT_SECONDS"

echo "Creating a smoke ticket for user id $SMOKE_USER_ID"
create_response="$(
  curl -fsS -X POST "$BASE_URL/tickets" \
    -H "Content-Type: application/json" \
    -H "X-User-ID: ${SMOKE_USER_ID}" \
    -d "{
      \"user_id\": ${SMOKE_USER_ID},
      \"title\": \"${MARKER} payment search smoke\",
      \"description\": \"Verify ticket search projection through Elasticsearch\",
      \"status\": \"open\",
      \"priority\": \"high\",
      \"category\": \"billing\",
      \"tags\": [\"smoke\", \"search\"]
    }"
)"

ticket_id="$(
  printf '%s' "$create_response" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])'
)"

wait_for_outbox_processed "$ticket_id"

echo "Searching for smoke ticket through Elasticsearch as user id $SMOKE_USER_ID"
for _ in $(seq 1 20); do
  search_response="$(
    curl -fsS -G "$BASE_URL/tickets/search" \
      -H "X-User-ID: ${SMOKE_USER_ID}" \
      --data-urlencode "q=$MARKER" \
      --data-urlencode "tag=smoke" \
      --data-urlencode "limit=5"
  )"

  if printf '%s' "$search_response" \
    | python3 -c '
import json
import sys

expected_id = int(sys.argv[1])
marker = sys.argv[2]
results = json.load(sys.stdin)

if not any(
    item.get("id") == expected_id and marker in item.get("title", "")
    for item in results
):
    raise SystemExit(1)
' "$ticket_id" "$MARKER"; then
    echo "Search smoke flow passed for ticket id $ticket_id"

    echo "Checking search metrics output"
    assert_metrics_contains "search_requests_total"
    assert_metrics_contains "search_request_duration_seconds"

    exit 0
  fi

  sleep 1
done

echo "Smoke ticket $ticket_id was not found in search results" >&2
show_docker_diagnostics
exit 1