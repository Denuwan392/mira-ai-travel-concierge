#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
state=$(mktemp -d)
port="${MIRA_MCP_TEST_PORT:-18019}"
export MIRA_DB="$state/mira-mcp.sqlite3"
export AS_OF_DATE=2026-11-19
export GEMINI_API_KEY= GEMINI_MODEL= LANGFUSE_PUBLIC_KEY= LANGFUSE_SECRET_KEY=
export MIRA_API_URL="http://127.0.0.1:$port"
export PYTHONPATH="$PWD/apps/api"

.venv/bin/python -m mira.serve --port "$port" >"$state/api.log" 2>&1 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true; rm -rf "$state"' EXIT

for n in $(seq 1 80); do
  if ! kill -0 "$api_pid" 2>/dev/null; then
    cat "$state/api.log"
    exit 1
  fi
  if curl -fsS "$MIRA_API_URL/api/health" >/dev/null 2>/dev/null; then
    break
  fi
  sleep 0.25
done

if ! curl -fsS "$MIRA_API_URL/api/health" >/dev/null 2>/dev/null; then
  echo "Backend failed health check on $MIRA_API_URL"
  cat "$state/api.log"
  exit 1
fi

node apps/web/mcp/smoke.mjs
