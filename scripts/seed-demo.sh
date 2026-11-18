#!/bin/sh
# Create (or with --reset rebuild) the demo organization in the running dev stack.
# Usage: ./scripts/seed-demo.sh [--reset]
set -e
cd "$(dirname "$0")/.."
docker compose exec backend python -m app.seed "$@"
