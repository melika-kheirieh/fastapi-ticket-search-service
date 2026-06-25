#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHONPATH=. python -m app.outbox.cli "$@"