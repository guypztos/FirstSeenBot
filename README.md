# FirstSeen

[![CI](https://github.com/guypztos/FirstSeenBot/actions/workflows/ci.yml/badge.svg)](https://github.com/guypztos/FirstSeenBot/actions/workflows/ci.yml)

A Telegram bot that polls company career feeds and alerts one user about new
student roles within commuting range. It reads only feeds the provider documents
as public (Lever and Greenhouse in version one) and links to the employer's own
posting.

- What it does and why: [SPEC.md](SPEC.md)
- Build order: [docs/PLAN.md](docs/PLAN.md)
- Design decisions and their trade-offs: [docs/DECISIONS.md](docs/DECISIONS.md)

## Status

Project skeleton only. The service answers `GET /health` and nothing else yet.
No feed is polled and no message is sent.

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs Python 3.13 and every dependency)
- Docker with Compose, for the local Postgres database
- GNU Make

## Setup

```sh
cp .env.example .env   # then fill in the real values; .env is git-ignored
make check             # creates .venv from uv.lock, then runs every quality gate
```

## Commands

| Command         | What it does                                                  |
|-----------------|---------------------------------------------------------------|
| `make check`    | `ruff format --check`, `ruff check`, `mypy` (strict), `pytest` |
| `make fmt`      | Format the code and apply safe lint fixes                     |
| `make coverage` | Run the tests with a coverage report                          |
| `make run`      | Serve the app on http://127.0.0.1:8000 with auto-reload        |
| `make db-up`    | Start local Postgres and wait until it is healthy             |
| `make db-down`  | Stop local Postgres (the data volume is kept)                 |

`make -k check` keeps going after a failure, so one run shows every failing gate.

## Continuous integration

Every push runs `make -k check` on GitHub Actions
([.github/workflows/ci.yml](.github/workflows/ci.yml)). The run also fails when
`uv.lock` no longer matches `pyproject.toml`. To fix that, run `uv lock` and commit
the result.

## Layout

```
src/firstseen/   application package
tests/           pytest suite; tests never make real network calls
docs/            plan and design decisions
.github/         the CI workflow
compose.yaml     local Postgres only
sources.yaml     the companies the bot polls
```

## Configuration

All secrets come from environment variables. Locally they live in `.env`, which is
git-ignored; `.env.example` lists the variable names. The only database URL in this
repository is the one for the local Docker database, which uses throwaway
credentials and listens on localhost only.
