.PHONY: install test run lint

install:
	python3 -m pip install -e '.[dev]'

test:
	MODEL_MODE=mock python3 -m pytest

run:
	MODEL_MODE=mock uvicorn app.main:app --reload

lint:
	python3 -m compileall -q app tests scripts

