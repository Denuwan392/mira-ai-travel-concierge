#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
  uv venv --python "${MIRA_PYTHON_VERSION:-3.13}"
fi
if ! cmp -s apps/api/requirements.lock .venv/.mira-lock; then
  uv pip sync --python .venv/bin/python apps/api/requirements.lock
  cp apps/api/requirements.lock .venv/.mira-lock
fi
if ! cmp -s apps/web/package-lock.json apps/web/node_modules/.mira-lock; then
  npm ci --prefix apps/web
  cp apps/web/package-lock.json apps/web/node_modules/.mira-lock
fi
if ! cmp -s apps/ceylon-compass/package-lock.json apps/ceylon-compass/node_modules/.mira-lock; then
  npm ci --prefix apps/ceylon-compass
  cp apps/ceylon-compass/package-lock.json apps/ceylon-compass/node_modules/.mira-lock
fi
