# Version-one build plan

One commit per step, each reviewed before it is committed. The scope is version one
in [SPEC.md](../SPEC.md). Decisions already made are in [DECISIONS.md](DECISIONS.md).

## Steps

| Done | # | Step | Tests that prove it |
|:---:|---|---|---|
| x | 0 | Skeleton: packaging, quality gates, local Postgres, `/health` | `/health` returns 200 |
| x | 1 | CI: GitHub Actions runs `make check` on push | first green run after a push |
|   | 2 | `Posting` model and Lever adapter (global and EU hosts). One approved request to capture the Mobileye fixture | field mapping, EU host chosen, User-Agent sent, non-200 and bad JSON raise `FetchError` |
|   | 3 | Greenhouse adapter, HTML description to plain text, adapter lookup by system. One approved request for one board | same set, plus HTML entities and list items become lines |
|   | 4 | Load and validate `sources.yaml` | real file loads 18 active entries, unknown system and duplicates rejected |
|   | 5 | `student` profile in `profiles.yaml`, pure matching functions | table-driven: "Full time" with Student in title, Hebrew title, Haifa marked far, "Internal Auditor" not a match, excluded title |
|   | 6 | Settings and JSON logging | missing secret fails at startup, log line is valid JSON |
|   | 7 | Four tables, first Alembic migration, `make migrate`. `make check` starts the database from here, and CI gets a Postgres service | upgrade, downgrade, upgrade on an empty database; both unique constraints hold |
|   | 8 | Company sync, posting upsert, closed and reopened detection | new, repeated, closed, reopened |
|   | 9 | Poll service: hourly guard, per-company isolation, `poll_runs` | failed fetch closes nothing, one failing company does not stop the rest, second poll within the hour is skipped |
|   | 10 | Telegram client and alert text | message has title, company, location, team, requirement lines, link; never the full description |
|   | 11 | Notifications: row first, send, then `sent_at` | no duplicate on repeat poll, unsent row retried, sent row never resent |
|   | 12 | `POST /jobs/poll` | rejected without the secret, summary returned with it; path added to the allowed list in `tests/test_routes.py` |
|   | 13 | `POST /telegram/webhook`, `/latest`, `/sources`, `/status` | wrong secret header rejected, other chat IDs ignored, each command's reply; path added to the allowed list |
|   | 14 | Dockerfile, deploy runbook in `docs/DEPLOY.md`, `make coverage` report | image builds and serves `/health` locally |
|   | 15 | Deploy and verify "Done means". Every cloud command needs the owner's go-ahead, budget alert first | `/health` answers on the public URL (confirms D27); three consecutive successful polls in `/status` |

## Dependencies approved on 2026-11-27

Each is installed in the step that first uses it. Anything not on this list needs
approval first.

| Package | Why | Step |
|---|---|---|
| fastapi, uvicorn, httpx | web framework, server, HTTP client | 0 (installed) |
| dev: ruff, mypy, pytest, pytest-cov, anyio | quality gates and async tests | 0 (installed) |
| pyyaml, dev: types-pyyaml | read `sources.yaml` and `profiles.yaml` | 4 |
| pydantic-settings | typed config from environment variables | 6 |
| sqlalchemy[asyncio], psycopg[binary], alembic | ORM, Postgres driver, migrations | 7 |

## Decisions still to confirm

These are recommendations. Each is confirmed, or changed, when its step starts, and
is then recorded in [DECISIONS.md](DECISIONS.md) in the same commit as the code.

| ID | Step | Recommendation | Trade-off and rejected alternative |
|---|---|---|---|
| D7 | 2 | Adapters receive the `httpx.AsyncClient` through the constructor; a test guard fails any real network call | Constructor injection, as in Java. Slightly more wiring than a global client |
| D8 | 2-3 | Fixtures: one real response per system, trimmed to a few postings, descriptions shortened, emails and phones removed | Not byte-identical to production. Rejected the full 1.1 MB dump: it republishes employer text in the repo |
| D9 | 2 | User-Agent contact comes from a required env var `FEED_CONTACT` | The owner chooses the value: the repo URL or a dedicated mailbox, not a main email address |
| D10 | 3 | HTML to text with the standard library's `html.parser` | We own the edge cases. Rejected BeautifulSoup: a package for one function |
| D11 | 3 | Strip emails and phone numbers from descriptions before storing | Recruiter names in free text cannot be detected reliably. Documented as a known limit |
| D12 | 4 | PyYAML `safe_load`, then validate with a pydantic model | Rejected switching to TOML (parser is built in) because the spec and the file are YAML |
| D13 | 5 | Whole-word match for English keywords, substring for Hebrew; a posting with several locations matches if any is in range; unknown location alerts with "location unclear" | More alerts to judge by hand, fewer missed roles. The owner supplies the "and nearby" towns |
| D14 | 7 | psycopg 3 as the driver | One driver for the async app and for Alembic, and one setting makes it work with Neon's pooled URL. Rejected asyncpg: faster and the tutorial default, but needs an async Alembic setup and two workarounds for the pooler |
| D15 | 7 | Database tests run on the real local Postgres; each test rolls back; a guard refuses any host but localhost | `make check` needs Docker running from step 7. Rejected SQLite: it lacks the Postgres `ON CONFLICT` upsert, so tests would not prove the real query |
| D16 | 7 | Store the feed's `created_at` (nullable); compute `requirement_lines` from the stored description instead of storing them | One column beyond the spec's table. Alternative: drop `created_at` from `Posting` |
| D17 | 8 | `sources.yaml` is the source of truth, synced into `companies` at the start of each poll; removed entries become inactive, never deleted | A little work per poll. Rejected a migration per company change |
| D18 | 9 | Hourly limit enforced in code from `poll_runs`, counting failed attempts too | A manual call or a wrong schedule cannot break the rule. Also applies in local development |
| D19 | 9 | A refusal (401, 403, 429) suspends that company until the owner resumes it by hand | Matches "stop polling it". Resuming is a documented one-line SQL command. Alternative: timed back-off that retries by itself |
| D20 | 9 | Poll companies one after another inside the request | 17 of 18 share the Greenhouse host, so this is the polite option, and Cloud Run only guarantees CPU while a request is open. Rejected parallel fetches and background tasks |
| D21 | 10 | Call the Telegram Bot API directly with httpx | Two API methods and three commands do not justify a bot framework. We write the small update model ourselves |
| D22 | 11 | Check every open posting against the profile on each poll; the unique constraint prevents repeats | Fixing a rule alerts on roles that are already open. Alternative, closer to the spec's wording: only first-seen postings, where a rule typo on day one hides open roles for good |
| D23 | 12 | Poll endpoint protected by a shared secret header, compared in constant time | Static secret in the Scheduler job. Rejected verifying Google's signed token in the app for now: the recommended method, but it needs another package |
| D24 | 14 | No connection pool in the app (Neon's pooler does it); migrations run by hand against the direct URL, never at startup | A few milliseconds per request. Avoids stale connections when Cloud Run and Neon both scale to zero |

## Spec gaps to settle

1. Matching "intern" as plain text also matches "Internal" and "International" (D13).
2. `Posting` has `created_at` and `requirement_lines`; the `postings` table has neither (D16).
3. No column records that a posting matched. `/latest` would read matches from `notifications`.
4. "Stop polling a refusing source" needs stored state the data model does not name (D19).
5. The local `.env` holds `PROD_DATABASE_URL` and `PROD_DATABASE_URL_DIRECT`. The app reads
   `DATABASE_URL` (local Postgres); the `PROD_` values are for deploys and migrations only.
