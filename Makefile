.PHONY: help install up down test lint fmt demo-test sandbox-smoke secret-scan check

help:
	@echo "  make install         create .venv and install Python deps"
	@echo "  make up              start the full stack in MOCK mode (docker compose)"
	@echo "  make down            stop the stack"
	@echo "  make test            unit + integration tests (no network, no keys)"
	@echo "  make demo-test       e2e demo scenarios (in-process, mock)"
	@echo "  make lint            ruff + mypy + dashboard tsc/eslint when present"
	@echo "  make sandbox-smoke   optional live sandbox checks (skipped without keys)"

install:
	python3 -m venv .venv
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -r requirements-dev.txt
	@echo "\nNow: cp .env.example .env  &&  make up"

up:
	@test -f .env || cp .env.example .env
	docker compose up --build -d
	@echo "waiting for API on :8000 …"
	@i=0; until curl -sf http://127.0.0.1:8000/healthz >/dev/null; do \
		i=$$((i+1)); \
		if [ $$i -ge 40 ]; then echo "API did not become healthy"; exit 1; fi; \
		sleep 2; \
	done
	@echo "API        http://localhost:8000"
	@echo "Dashboard  http://localhost:8000/"
	@echo "Demo shop  http://localhost:3000"

down:
	docker compose down

test:
	PAYPAL_ENVIRONMENT=MOCK LLM_MODE=mock \
		python -m pytest -q tests/unit tests/integration

lint:
	ruff check flatline tests scripts
	mypy flatline
	@if [ -f dashboard/package.json ]; then \
		(cd dashboard && npm run lint); \
	fi

fmt:
	ruff check --fix flatline tests scripts
	ruff format flatline tests scripts

demo-test:
	PAYPAL_ENVIRONMENT=MOCK LLM_MODE=mock \
		python -m pytest -q tests/e2e/test_demo_scenarios.py

sandbox-smoke:
	PAYPAL_ENVIRONMENT=SANDBOX \
		python -m pytest -q tests/integration/test_sandbox_smoke.py

secret-scan:
	python scripts/secret_scan.py

check: lint test secret-scan
