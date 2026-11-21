PYTHON ?= .venv/bin/python
export PYTHONPATH := $(CURDIR)/apps/api
export NEXT_TELEMETRY_DISABLED := 1
export COPILOTKIT_TELEMETRY_DISABLED := 1

.PHONY: dev setup test eval lint build smoke browser
dev:
	./scripts/dev.sh

setup:
	./scripts/setup.sh

test:
	npm --prefix apps/ceylon-compass test
	$(PYTHON) -m pytest -q apps/api/tests

eval: test
	$(PYTHON) evals/runner.py

lint:
	$(PYTHON) -m compileall -q apps/api/mira evals
	npm --prefix apps/web run typecheck
	cd apps/ceylon-compass && ./node_modules/.bin/tsc --noEmit

build:
	npm --prefix apps/ceylon-compass run build
	npm --prefix apps/web run build

smoke:
	node scripts/smoke.mjs

browser:
	npm --prefix apps/web test

.PHONY: mcp-smoke
mcp-smoke:
	node apps/web/mcp/smoke.mjs

.PHONY: notebook-browser
notebook-browser:
	node apps/ceylon-compass/tests/notebook.cjs
