# Every tool runs through `uv run`, which first syncs .venv to uv.lock. A fresh
# clone therefore needs no setup step before `make check`.
#
# The four quality gates are separate targets so that `make -k check` keeps going
# after a failure and shows every failing gate in one run.

.PHONY: check fmt-check lint typecheck test fmt coverage run db-up db-down

check: fmt-check lint typecheck test

fmt-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy

test:
	uv run pytest

fmt:
	uv run ruff format .
	uv run ruff check --fix .

coverage:
	uv run pytest --cov=firstseen --cov-report=term-missing

# --factory: uvicorn calls create_app() itself; there is no module-level app object.
run:
	uv run uvicorn --factory firstseen.main:create_app --reload

# --wait blocks until the healthcheck passes, so the next command can connect.
db-up:
	docker compose up -d --wait db

db-down:
	docker compose down
