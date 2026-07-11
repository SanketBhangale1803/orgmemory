SHELL := /bin/bash
BACKEND_PY := backend/.venv/bin/python
MCP_PY := mcp_server/.venv/bin/python

.PHONY: runbook dev backend frontend mcp test lint ci format demo reset docker-up docker-down arcade-init graph-check benchmark

runbook:
	docker compose --profile mcp up --build

dev: docker-up

docker-up:
	docker compose --profile mcp up --build -d

docker-down:
	docker compose --profile mcp down

$(BACKEND_PY):
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt

$(MCP_PY):
	python3 -m venv mcp_server/.venv
	mcp_server/.venv/bin/pip install -r mcp_server/requirements.txt

frontend/node_modules:
	cd frontend && npm install

backend: $(BACKEND_PY)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend: frontend/node_modules
	cd frontend && npm run dev

mcp: $(MCP_PY)
	RUNBOOK_API_URL=$${RUNBOOK_API_URL:-http://localhost:8000} $(MCP_PY) mcp_server/server.py

test: $(BACKEND_PY) frontend/node_modules
	cd backend && .venv/bin/pytest
	cd frontend && npm test

lint: $(BACKEND_PY) frontend/node_modules
	cd backend && .venv/bin/ruff check app tests scripts && .venv/bin/black --check app tests scripts
	cd frontend && npx tsc --noEmit

ci: test lint
	cd frontend && npm run build

format: $(BACKEND_PY)
	cd backend && .venv/bin/ruff check --fix app tests scripts && .venv/bin/black app tests scripts

arcade-init:
	docker compose up -d arcadedb
	docker compose run --rm backend python scripts/init_arcade.py

graph-check:
	docker compose exec backend python scripts/graph_check.py

demo:
	docker compose exec backend python scripts/load_demo.py

reset:
	docker compose exec backend python scripts/reset.py

benchmark:
	$(MAKE) -C ../hcag benchmark
