# FirstSeen: student job alerts bot (portfolio project)

## What this is
A Telegram bot that polls company career feeds and alerts one user about new
student roles. Built by a third-year CS student as a portfolio project.
The owner must be able to explain and defend every design decision in an interview.
Read SPEC.md before doing anything. Its compliance rules are binding.

## Stack
- Python 3.13, FastAPI, httpx (async), SQLAlchemy 2 (async) with Alembic migrations.
- Postgres. Local development uses Postgres in Docker Compose.
- pytest, ruff, mypy (strict).
- Deployed to Google Cloud Run. Do not deploy or create cloud resources unasked.

## Scope
Build version one in SPEC.md only. Anything under "Out of scope" or in later
roadmap stages needs my explicit approval first.

## How to work with me
- Propose a short plan before writing code, and wait for approval.
- One small step at a time. Stop after each for my review before committing.
- Explain non-obvious choices briefly, including the alternative you rejected.
- I am stronger in Java than Python. Point out Python idioms when you use them.
- Verify claims by running things. Show command output as evidence.

## Quality gates (run after every change, before saying a step is done)
All through one command, `make check`:
1. `ruff format --check` and `ruff check`
2. `mypy` in strict mode
3. `pytest`
Coverage is a separate `make coverage` target, reported when version one is done.
Fix failures. Do not suppress a lint or type error without asking.

## Rules specific to this project
- Tests never make real network calls. Use saved responses in tests/fixtures/.
- Only documented public feed endpoints. No HTML scraping, no logins, no bypassing
  rate limits or bot protection.
- Never poll a company more than once per hour, including during development.
- Secrets come from environment variables (a git-ignored `.env` locally). Never
  write a real token, chat ID or database URL into the repo, logs or test fixtures.
  The one exception is the localhost-only URL of the Docker Compose database, which
  uses throwaway credentials (docs/DECISIONS.md, D25).
- No new dependencies without asking.

## Documentation and commits
- Comment the why, not the what. Public functions get a short docstring.
- Record design decisions in docs/DECISIONS.md, in the same commit as the code.
- Commit after each approved step once `make check` passes. Never push without asking.
- Keep README.md current with setup and run instructions.

## Commands
Update as soon as the real commands exist.
- Check: `make check` (`make -k check` shows every failing gate in one run)
- Format: `make fmt`
- Coverage: `make coverage`
- Run locally: `make run` (serves http://127.0.0.1:8000)
- Local database: `make db-up` and `make db-down`
- Migrate database: not available yet. Arrives with step 7 of docs/PLAN.md.

## Current status
Source survey done (see the appendix in SPEC.md). Skeleton and CI built: steps 0
and 1 of docs/PLAN.md. Next is step 2 (`Posting` model and Lever adapter). Follow
docs/PLAN.md in order, one step per commit, and confirm each step's open decisions
(D7 to D24) before building it.
