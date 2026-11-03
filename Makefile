.PHONY: install test run lint check adversarial smoke-staging prep-demo db-up db-down migrate seed

PYTHON ?= python3.11

install:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	MODEL_MODE=mock $(PYTHON) -m pytest

check: lint test

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
	$(PYTHON) -m compileall -q app tests scripts

