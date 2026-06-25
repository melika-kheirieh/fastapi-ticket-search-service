#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
MARKER="smoke-$(date +%s)"
UPDATED_MARKER="${MARKER}-updated"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

wait_for_api() {
  for _ in $(seq 1 30); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      return 0
    fi

    sleep 1
  done

  echo "API did not become ready at $BASE_URL" >&2
  exit 1
}

wait_for_elasticsearch() {
  for _ in $(seq 1 60); do
    if docker compose exec -T api python - <<'PY' >/dev/null 2>&1
from app.search.client import create_elasticsearch_client

client = create_elasticsearch_client()
if not client.ping():
    raise SystemExit(1)
PY
    then
      return 0
    fi

    sleep 1
  done

  echo "Elasticsearch did not become ready from the API container" >&2
  exit 1
}

process_outbox() {
  echo "Processing outbox events"
  docker compose exec -T api python -m app.outbox.cli --limit 20 >/dev/null
}

search_contains_ticket() {
  local expected_id="$1"
  local marker="$2"

  for _ in $(seq 1 10); do
    search_response="$(
      curl -fsS -G "$BASE_URL/tickets/search" \
        --data-urlencode "q=$marker" \
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
      ' "$expected_id" "$marker"; then
      return 0
    fi

    sleep 1
  done

  return 1
}

search_does_not_contain_ticket() {
  local expected_id="$1"
  local marker="$2"

  for _ in $(seq 1 10); do
    search_response="$(
      curl -fsS -G "$BASE_URL/tickets/search" \
        --data-urlencode "q=$marker" \
        --data-urlencode "tag=smoke" \
        --data-urlencode "limit=5"
    )"

    if printf '%s' "$search_response" \
      | python3 -c '
import json
import sys

expected_id = int(sys.argv[1])
results = json.load(sys.stdin)

if any(item.get("id") == expected_id for item in results):
    raise SystemExit(1)
      ' "$expected_id"; then
      return 0
    fi

    sleep 1
  done

  return 1
}

require_command curl
require_command docker
require_command python3

echo "Checking API health at $BASE_URL"
wait_for_api

echo "Checking Elasticsearch readiness"
wait_for_elasticsearch

echo "Ensuring Elasticsearch index exists"
docker compose exec -T api python -m app.search.setup >/dev/null

echo "Creating a smoke ticket"
create_response="$(
  curl -fsS -X POST "$BASE_URL/tickets" \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\": 9001,
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

process_outbox

echo "Searching for created smoke ticket through Elasticsearch"
if ! search_contains_ticket "$ticket_id" "$MARKER"; then
  echo "Created smoke ticket $ticket_id was not found in search results" >&2
  exit 1
fi

echo "Updating smoke ticket"
curl -fsS -X PATCH "$BASE_URL/tickets/$ticket_id" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"${UPDATED_MARKER} payment search smoke\",
    \"status\": \"in_progress\"
  }" >/dev/null

process_outbox

echo "Searching for updated smoke ticket through Elasticsearch"
if ! search_contains_ticket "$ticket_id" "$UPDATED_MARKER"; then
  echo "Updated smoke ticket $ticket_id was not found in search results" >&2
  exit 1
fi

echo "Deleting smoke ticket"
curl -fsS -X DELETE "$BASE_URL/tickets/$ticket_id" >/dev/null

process_outbox

echo "Verifying deleted smoke ticket is removed from Elasticsearch"
if ! search_does_not_contain_ticket "$ticket_id" "$UPDATED_MARKER"; then
  echo "Deleted smoke ticket $ticket_id was still found in search results" >&2
  exit 1
fi

echo "Outbox-backed search smoke flow passed for ticket id $ticket_id"