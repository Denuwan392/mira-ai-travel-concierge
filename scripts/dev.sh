#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
export PYTHONPATH="$PWD/apps/api"
export AS_OF_DATE="${AS_OF_DATE:-2026-11-19}"
export MIRA_ORIGIN="${MIRA_ORIGIN:-http://127.0.0.1:3000}"
export NEXT_TELEMETRY_DISABLED=1
export COPILOTKIT_TELEMETRY_DISABLED=1

./scripts/setup.sh
compass_pid=
api_pid=
web_pid=
cleanup() {
  [ -z "$compass_pid" ] || kill "$compass_pid" 2>/dev/null || true
  [ -z "$api_pid" ] || kill "$api_pid" 2>/dev/null || true
  [ -z "$web_pid" ] || kill "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

.venv/bin/python -m uvicorn mira.main:app --host 127.0.0.1 --port 8000 --no-access-log &
api_pid=$!
for delay in 1 2 3 4 5 6 7 8 9 10; do
  if health=$(curl -fsS http://127.0.0.1:8000/api/health 2>/dev/null); then
    printf 'Mira data health %s\n' "$health"
    break
  fi
  kill -0 "$api_pid"
  sleep 1
done
apps/web/node_modules/.bin/next dev apps/web --hostname 127.0.0.1 --port 3000 &
web_pid=$!
(cd apps/ceylon-compass && exec ./node_modules/.bin/vite dev --host 127.0.0.1 --port 5175 --strictPort) &
compass_pid=$!
wait "$compass_pid"
