PYTHON := python3
PIP := pip
PYTEST_ARGS ?=
CORDIS_ARGS ?=
EVAL_ARGS ?=

.PHONY: help install install-dev run run-reload docker-up docker-down lint format test test-tools test-live clean precommit hooks refresh-cordis

help:
	@echo "Common commands:"
	@echo "  make install        Install prod dependencies"
	@echo "  make install-dev    Install dev dependencies (ruff/black/isort/pytest/pre-commit)"
	@echo "  make run            Run API (uvicorn main:app)"
	@echo "  make run-reload     Run API with reload"
	@echo "  make docker-up      Start services via docker-compose"
	@echo "  make docker-down    Stop services"
	@echo "  make lint           Run ruff (lint)"
	@echo "  make format         Run ruff format + isort + black"
	@echo "  make test           Run guarded offline tests"
	@echo "  make test-tools     Check tools against read-only source evidence (zero model calls)"
	@echo "  make test-live      Run compact source-backed questions (30 model requests maximum)"
	@echo "  make refresh-cordis CORDIS_ARGS='--export data/cordis_exports/FILE.zip [--apply]'"
	@echo "  make precommit      Run pre-commit on all files"
	@echo "  make hooks          Install pre-commit git hooks"

install:
	$(PIP) install -r requirements.txt

install-dev: install
	$(PIP) install -r requirements-dev.txt

run:
	uvicorn main:app --host 0.0.0.0 --port 8000

run-reload:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker compose up -d

docker-down:
	docker compose down

lint:
	ruff check app tests .

format:
	ruff format app tests .
	isort app tests .
	black app tests .

test:
	$(PYTHON) scripts/test_offline.py $(PYTEST_ARGS)

test-tools:
	$(PYTHON) scripts/evaluate_tools.py --mode contracts $(EVAL_ARGS)

test-live:
	$(PYTHON) scripts/evaluate_tools.py --mode questions --max-requests 30 $(EVAL_ARGS)

precommit:
	pre-commit run --all-files

hooks:
	pre-commit install

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

# Run in the API environment, where database/embedding settings are configured.
refresh-cordis:
	docker compose exec -T -e PYTHONPATH=/app api python scripts/refresh_cordis.py $(CORDIS_ARGS)
