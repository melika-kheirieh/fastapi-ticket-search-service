#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
MARKER="smoke-$(date +%s)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

wait_for_api() {
  for _ in $(seq 1 30); do
    if curl -fsS "$BASE_URL/health" >/dev/null; then
      return 0
    fi
    sleep 1
  done

  echo "API did not become ready at $BASE_URL" >&2
  exit 1
}

require_command curl
require_command docker
require_command python3

echo "Checking API health at $BASE_URL"
wait_for_api

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

echo "Reindexing tickets into Elasticsearch"
docker compose exec -T api python -m app.search.reindex >/dev/null

echo "Searching for smoke ticket through Elasticsearch"
for _ in $(seq 1 10); do
  search_response="$(
    curl -fsS -G "$BASE_URL/tickets/search" \
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
    exit 0
  fi

  sleep 1
done

echo "Smoke ticket $ticket_id was not found in search results" >&2
exit 1