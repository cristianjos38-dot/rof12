.PHONY: install test run lint check db-up db-down migrate seed

install:
	python3 -m pip install -e '.[dev]'

test:
	MODEL_MODE=mock python3 -m pytest

check: lint test

run:
	MODEL_MODE=mock uvicorn app.main:app --reload

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	alembic upgrade head

seed:
	DATABASE_OWNER_URL=$${DATABASE_OWNER_URL:-postgresql+psycopg://rof12_owner:rof12_owner_dev_only@localhost:5432/rof12} python3 scripts/seed.py

lint:
	python3 -m compileall -q app tests scripts

