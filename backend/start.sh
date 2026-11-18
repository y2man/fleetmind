#!/bin/sh
# Container start: migrate, optionally seed demo data, then serve.
set -e
alembic upgrade head
if [ "$SEED_DEMO_ON_START" = "true" ]; then
  # Idempotent. Refuses by itself when ENVIRONMENT=production; a failure here never blocks startup.
  python -m app.seed || echo "start: demo seed skipped (see message above)"
fi
if [ "$ENVIRONMENT" = "production" ]; then
  # Live tracking and alert dedupe are still process-local; use one worker until those move to shared infrastructure.
  # --proxy-headers makes request.client the real caller behind nginx; keep this port unpublished.
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers --forwarded-allow-ips='*'
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
