#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

cli_mira_db=${MIRA_DB-}
cli_log_level=${LOG_LEVEL-}
cli_log_format=${LOG_FORMAT-}
cli_llm_details=${LOG_LLM_DETAILS-}
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
if [ -n "$cli_mira_db" ]; then
  export MIRA_DB="$cli_mira_db"
fi
export LOG_LEVEL="${cli_log_level:-${LOG_LEVEL:-INFO}}"
export LOG_FORMAT="${cli_log_format:-${LOG_FORMAT:-pretty}}"
export LOG_LLM_DETAILS="${cli_llm_details:-${LOG_LLM_DETAILS:-false}}"
export PYTHONPATH="$PWD/apps/api"
export AS_OF_DATE="${AS_OF_DATE:-2026-11-19}"
export MIRA_ORIGIN="${MIRA_ORIGIN:-http://127.0.0.1:3000}"
export NEXT_TELEMETRY_DISABLED=1
export COPILOTKIT_TELEMETRY_DISABLED=1

export PYTHONUNBUFFERED=1
if [ -t 2 ]; then
  export MIRA_DEV_COLOR=1
fi
if [ -x .venv/bin/python ]; then
  .venv/bin/python scripts/dev.py --check-ports
fi
./scripts/setup.sh
npm --prefix apps/ceylon-compass run workspace:build
exec .venv/bin/python scripts/dev.py
