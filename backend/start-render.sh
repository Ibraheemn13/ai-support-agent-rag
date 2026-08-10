#!/usr/bin/env bash
set -euo pipefail

# Render's free plan has no background-worker service. For the portfolio demo,
# one web service runs the API and one RQ worker against the same Redis queue.
# A production deployment should split these into independently scaled services.
python -m alembic upgrade head

python worker.py &
worker_pid=$!

python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --proxy-headers \
  --forwarded-allow-ips="*" &
api_pid=$!

shutdown() {
  trap - EXIT INT TERM
  kill -TERM "$api_pid" "$worker_pid" 2>/dev/null || true
  wait "$api_pid" "$worker_pid" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

# If either process exits, stop the other so Render restarts the whole service.
set +e
wait -n "$api_pid" "$worker_pid"
status=$?
set -e
exit "$status"
