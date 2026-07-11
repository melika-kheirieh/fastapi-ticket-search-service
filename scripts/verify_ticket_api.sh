#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
VERIFY_USER_ID="${VERIFY_USER_ID:-1}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

response_file="$TMP_DIR/response.json"

request() {
  local method="$1"
  local path="$2"
  local expected_status="$3"
  local payload="${4:-}"

  local status_code

  if [[ -n "$payload" ]]; then
    status_code="$(
      curl -sS \
        -o "$response_file" \
        -w "%{http_code}" \
        -X "$method" \
        "$BASE_URL$path" \
        -H "Content-Type: application/json" \
        -H "X-User-ID: ${VERIFY_USER_ID}" \
        -d "$payload"
    )"
  else
    status_code="$(
      curl -sS \
        -o "$response_file" \
        -w "%{http_code}" \
        -X "$method" \
        "$BASE_URL$path" \
        -H "X-User-ID: ${VERIFY_USER_ID}"
    )"
  fi

  if [[ "$status_code" != "$expected_status" ]]; then
    echo "FAILED: $method $path"
    echo "Expected status: $expected_status"
    echo "Actual status:   $status_code"
    echo "Response:"
    cat "$response_file"
    echo
    exit 1
  fi

  echo "OK: $method $path -> $status_code"
}

json_field() {
  local field="$1"

  python - "$field" "$response_file" <<'PY'
import json
import sys

field = sys.argv[1]
path = sys.argv[2]

with open(path, "r", encoding="utf-8") as file:
    data = json.load(file)

value = data[field]
print(value)
PY
}

assert_json_field_equals() {
  local field="$1"
  local expected="$2"

  local actual
  actual="$(json_field "$field")"

  if [[ "$actual" != "$expected" ]]; then
    echo "FAILED: expected JSON field '$field' to be '$expected', got '$actual'"
    echo "Response:"
    cat "$response_file"
    echo
    exit 1
  fi

  echo "OK: JSON field $field == $expected"
}

echo "Verifying ticket API at $BASE_URL as user id $VERIFY_USER_ID"

request "GET" "/health" "200"

ticket_payload="$(
  cat <<JSON
{
  "user_id": ${VERIFY_USER_ID},
  "title": "Ticket API verification",
  "description": "Created by the ticket API verification script",
  "status": "open",
  "priority": "high",
  "category": "auth",
  "tags": ["verification", "auth"]
}
JSON
)"

request "POST" "/tickets" "201" "$ticket_payload"
ticket_id="$(json_field "id")"

echo "Created ticket id: $ticket_id"

request "GET" "/tickets/$ticket_id" "200"
assert_json_field_equals "id" "$ticket_id"
assert_json_field_equals "user_id" "$VERIFY_USER_ID"
assert_json_field_equals "status" "open"
assert_json_field_equals "priority" "high"
assert_json_field_equals "category" "auth"

request "GET" "/tickets?user_id=${VERIFY_USER_ID}" "200"
request "GET" "/tickets?status=open" "200"
request "GET" "/tickets?priority=high" "200"
request "GET" "/tickets?category=auth&limit=10&offset=0" "200"

request "GET" "/tickets?limit=101" "422"
request "GET" "/tickets?user_id=0" "422"
request "GET" "/tickets?offset=-1" "422"

update_payload='{
  "status": "closed",
  "priority": "medium"
}'

request "PATCH" "/tickets/$ticket_id" "200" "$update_payload"
assert_json_field_equals "status" "closed"
assert_json_field_equals "priority" "medium"

request "DELETE" "/tickets/$ticket_id" "204"
request "GET" "/tickets/$ticket_id" "404"

echo "Ticket API verification passed."