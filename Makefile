.PHONY: bootstrap test lint run-backend run-mcp run-war-room seed smoke-eval demo

PYTHON ?= python3.12
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	$(PY) scripts/seed_db.py

test:
	$(PYTEST) -q

lint:
	$(RUFF) check packages apps scripts

run-backend:
	RASEN_TRANSPORT=$${RASEN_TRANSPORT:-fake} $(VENV)/bin/uvicorn app.main:app --app-dir apps/backend --reload --port 8000

run-mcp:
	$(VENV)/bin/uvicorn app.main:app --app-dir apps/mcp-server --reload --port 8001

run-war-room:
	cd apps/war-room && npm install && npm run dev -- --port 3000

seed:
	$(PY) scripts/seed_db.py

smoke-eval:
	PYTHONPATH=apps/eval-harness:packages/shared:packages/rasen-client $(PY) -m rasenloop_eval.runner --transport fake

demo:
	@echo "See docs/demo-playbook.md"
	@echo "1) make run-backend"
	@echo "2) make run-mcp"
	@echo "3) make run-war-room"
	@echo "4) open http://localhost:3000"
