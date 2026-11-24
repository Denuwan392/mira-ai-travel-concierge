#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
state=$(mktemp -d)
export MIRA_DB="$state/mira.sqlite3" MIRA_STAFF_TOKEN="$(openssl rand -hex 32)"
export MIRA_ADMIN_EMAIL=console@example.test MIRA_ADMIN_PASSWORD="$(openssl rand -hex 24)"
export MIRA_WORKSPACE_TEST=1 MIRA_TEST_STAFF_PASSWORD="$MIRA_ADMIN_PASSWORD"
export AS_OF_DATE=2026-11-19 GEMINI_API_KEY= GEMINI_MODEL= LANGFUSE_PUBLIC_KEY= LANGFUSE_SECRET_KEY=
export MIRA_ORIGIN=http://127.0.0.1:15175 MIRA_WEB_URL=http://127.0.0.1:15175 MIRA_API_URL=http://127.0.0.1:18008
export PYTHONPATH="$PWD/apps/api"
npm --prefix apps/ceylon-compass run build >"$state/build.log" || { cat "$state/build.log"; exit 1; }
.venv/bin/python -m mira.serve --port 18008 >"$state/api.log" 2>&1 &
api_pid=$!
PORT=15175 HOST=127.0.0.1 node apps/ceylon-compass/.output/server/index.mjs >"$state/web.log" 2>&1 &
web_pid=$!
trap 'kill "$api_pid" "$web_pid" 2>/dev/null || true' EXIT
for n in $(seq 1 80); do
  if ! kill -0 "$api_pid" || ! kill -0 "$web_pid"; then cat "$state/api.log" "$state/web.log"; exit 1; fi
  if curl -fsS "$MIRA_WEB_URL/api/health" >/dev/null 2>/dev/null; then break; fi
  sleep .25
done
cd apps/web
./node_modules/.bin/playwright test workspace.spec.ts
