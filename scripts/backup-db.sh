#!/bin/sh
# Dump Supabase PostgreSQL to ./backups/fleetmind-YYYYmmdd-HHMMSS.sql.gz
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo "Missing .env; configure DATABASE_URL before backing up." >&2
  exit 1
fi
mkdir -p backups
out="backups/fleetmind-$(date +%Y%m%d-%H%M%S).sql.gz"
tmp="$(mktemp)"
trap 'rm -f "$tmp" "$out"' EXIT HUP INT TERM
docker run --rm --env-file .env postgres:16-alpine sh -ec 'test -n "$DATABASE_URL"; pg_dump "$DATABASE_URL"' > "$tmp"
gzip -c "$tmp" > "$out"
rm -f "$tmp"
trap - EXIT HUP INT TERM
echo "wrote $out"
