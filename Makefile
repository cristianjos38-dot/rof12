.PHONY: install test run lint check adversarial smoke-staging prep-demo db-up db-down migrate seed typecheck audit

# Override with `make PYTHON=python` in CI or another managed environment.
PYTHON ?= python3.11

install:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	MODEL_MODE=mock $(PYTHON) -m pytest --cov=rof12 --cov=app --cov-report=term-missing

check: lint typecheck audit test

adversarial:
	MODEL_MODE=mock $(PYTHON) -m pytest tests/adversarial tests/meta -q

run:
	MODEL_MODE=mock uvicorn app.main:app --reload

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	alembic upgrade head

seed:
	DATABASE_OWNER_URL=$${DATABASE_OWNER_URL:-postgresql+psycopg://rof12_owner:rof12_owner_dev_only@localhost:5433/rof12} $(PYTHON) scripts/seed.py

smoke-staging:
	$(PYTHON) scripts/smoke_staging.py

prep-demo:
	bash scripts/prep_demo.sh

lint:
	$(PYTHON) -m ruff check app rof12 scripts tests
	$(PYTHON) -m ruff format --check app/__init__.py
	$(PYTHON) -m compileall -q app tests scripts

typecheck:
	$(PYTHON) -m mypy --strict --ignore-missing-imports app/security/policy_engine.py app/security/security_gate.py app/verification/verityflow.py rof12/core.py --disable-error-code=no-untyped-def --disable-error-code=no-untyped-call --disable-error-code=type-arg

audit:
	$(PYTHON) -m pip_audit --skip-editable

