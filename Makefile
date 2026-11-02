.PHONY: install test run lint check db-up db-down migrate

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

lint:
	python3 -m compileall -q app tests scripts

