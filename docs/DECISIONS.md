# Design decisions

One entry per decision, in the order they were made. Each records what was chosen,
why, what was rejected, and what it costs. IDs match [PLAN.md](PLAN.md); decisions
D7 to D24 are listed there as recommendations and move here when their step is built.

## D1. uv with a committed lockfile (2026-11-27)
- **Decision:** Dependencies are declared in `pyproject.toml` and pinned exactly,
  including transitive packages, in `uv.lock`. Development tools live in a `dev`
  dependency group, so a production install can leave them out.
- **Why:** The lockfile makes every machine and CI install the same versions. It
  plays the role of a Maven or Gradle lockfile.
- **Rejected:** pip with `requirements.txt`. It has no lock for transitive packages
  unless a second tool generates one, and then two files must be kept in sync.
- **Trade-off:** Anyone who builds the project must install uv first.

## D2. src layout, installed into the virtual environment (2026-11-27)
- **Decision:** Application code lives in `src/firstseen/`. uv builds it with its own
  build backend (`uv_build`) and installs it into `.venv` in editable mode.
- **Why:** Tests import the installed package, exactly as production will. With a
  flat layout Python would import the folder in the working directory, which can
  hide a packaging mistake until deployment.
- **Rejected:** Flat layout (`firstseen/` at the repo root); and hatchling as the
  build backend, which is equally capable but one more tool to know.
- **Trade-off:** One extra directory level.

## D3. Strict gates: ruff rules, mypy strict on tests, warnings as errors (2026-11-27)
- **Decision:** ruff checks rule sets `E F W I B UP SIM RUF ASYNC DTZ` with a line
  length of 100. mypy runs in strict mode over `src` and `tests`. pytest treats every
  warning as an error and rejects unknown markers and config keys.
- **Why:** `ASYNC` flags blocking calls inside async functions and `DTZ` forbids
  timezone-naive datetimes, the two mistakes most likely in a polling service that
  stores timestamps. A forgotten `await` is only a `RuntimeWarning` in Python, so
  without warnings-as-errors it would pass silently.
- **Evidence:** A throwaway test with `asyncio.sleep(0)` and no `await` failed both
  mypy (`unused-coroutine`) and pytest (`coroutine 'sleep' was never awaited`).
- **Rejected:** ruff's security rule set (`S`): it flags every `assert` in the tests,
  which would need a blanket exemption.
- **Trade-off:** Test functions need type annotations (`-> None`). A deprecation
  warning from a library can break the build until it is explicitly allowed.

## D4. Local Postgres 18, Debian-based image (2026-11-27)
- **Decision:** `compose.yaml` runs `postgres:18`, published on `127.0.0.1` only.
- **Why:** Same engine and major version as production (the Neon project runs 18),
  so a query or migration that works locally is not surprised by a version
  difference. The Debian image uses the same C library family as Neon, so text sorts
  the same way in both; the smaller alpine image does not.
- **Detail:** From version 18 the image stores data in a per-version folder
  (`/var/lib/postgresql/18/docker`), so the volume is mounted at `/var/lib/postgresql`
  and not at `/var/lib/postgresql/data` as in older guides.
- **Evidence:** `select version()` returned PostgreSQL 18.7, and a table created
  before `make db-down` was still there after `make db-up`.
- **Trade-off:** Larger image than alpine. When Neon is upgraded to a new major
  version, the image tag must be changed by hand.

## D5. One-week cooldown on new releases (2026-11-27)
- **Decision:** `exclude-newer` in `pyproject.toml` makes uv ignore anything published
  after a fixed date, set one week back when dependencies are added or upgraded.
- **Why:** A compromised or broken release is usually caught within days. Waiting a
  week keeps such a release out of the lockfile.
- **Evidence:** httpx 0.29.0 was published on 2026-11-26. The lock resolved to 0.28.1.
- **Rejected:** Always taking the newest release.
- **Trade-off:** Fixes arrive a week late unless the date is moved by hand.

## D6. Async tests with anyio's pytest plugin, HTTP faked with httpx transports (2026-11-27)
- **Decision:** Async tests carry `pytest.mark.anyio` and run on asyncio only (the
  `anyio_backend` fixture in `tests/conftest.py`). HTTP is faked with transports that
  ship with httpx: `ASGITransport` to call the app in-process, and `MockTransport`
  for outbound calls from step 2.
- **Why:** Both are already installed as part of httpx and Starlette, and this is the
  approach FastAPI's documentation uses. No test opens a socket.
- **Rejected:** pytest-asyncio and respx. Better known, but two more packages.
- **Trade-off:** Each async test module needs the marker line.

## D25. The localhost database URL may be committed (2026-11-27)
- **Decision:** `compose.yaml` and `.env.example` contain the URL and password of the
  local Docker database. No real token, chat ID or database URL is ever committed.
- **Why:** A fresh clone runs without manual setup. The credentials protect nothing:
  the container holds only development data and listens on localhost only.
- **Rejected:** Reading the local password from `.env`. Stricter, but it adds a manual
  step to every clone and a secret to CI for a database that holds nothing private.
- **Trade-off:** Secret scanners may flag the harmless URL.
- **Call:** Reviewed again the same day. The owner asked whether keeping the URL only
  in `.env` would do. It would work, and committing it is not required. It stays
  committed for three reasons: a fresh clone can start the database without creating
  `.env`; CI cannot read `.env`; and `.env` also holds the production URLs, so tests
  should take their database URL from a fixed localhost value and never from that
  file. One wrong variable name there would point the test suite at Neon, and the
  migration test drops tables. `SPEC.md` now states the exception.

## D26. Application factory instead of a module-level app (2026-11-27)
- **Decision:** `firstseen.main.create_app()` builds the FastAPI app. uvicorn is
  started with `--factory`.
- **Why:** Each test builds its own app, so no state leaks between tests. Importing
  the module has no side effects, which matters from step 6, when building the app
  starts to read settings from the environment.
- **Rejected:** `app = FastAPI()` at module level, the form most tutorials show.
- **Trade-off:** The run command needs the `--factory` flag.

## D27. The liveness endpoint is `/health`, not `/healthz` (2026-11-27)
- **Decision:** The endpoint is `GET /health`. `SPEC.md` said `/healthz` and was
  changed in the same commit.
- **Why:** The service is deployed on Cloud Run, which reserves some URL paths ending
  in "z". Google's front end answers a reserved path itself with a 404, so the
  request never reaches the container. The endpoint would have worked locally and in
  tests and failed only after deployment.
- **Evidence:** Google's "Known issues in Cloud Run" page lists reserved URL paths
  and recommends avoiding every path that ends in z. One forum report describes
  `/healthz` returning 404 until it was renamed to `/health`. This comes from a
  search summary of that page, not from reading it directly, and has not been tried
  on a deployed service. Step 15 checks `/health` on the public URL.
- **Rejected:** Keeping `/healthz`, the name Kubernetes made common, and finding out
  at deploy time.
- **Trade-off:** A less conventional name than `healthz`.

## D28. Stop hook runs `make check`, blocking once per turn (2026-11-27)
- **Decision:** `.claude/settings.json` registers a Claude Code Stop hook,
  `.claude/hooks/stop-make-check.sh`. It runs `make -k check` each time Claude is
  about to finish a turn. If a gate fails it exits with code 2, which blocks the
  stop and gives Claude the failing output. If Claude was already blocked once in
  the same turn and the check still fails, the hook lets Claude stop and shows a
  warning instead.
- **Why:** CLAUDE.md requires the gates after every change. The hook makes that a
  mechanism instead of a promise. The once-per-turn limit exists because some
  failures cannot be fixed by Claude: Docker not running, or a test the owner broke
  on purpose. Blocking without a limit would keep Claude working forever on those.
- **Evidence:** Run by hand against a throwaway test broken on purpose: exit code 2
  with the pytest failure on stderr; with `stop_hook_active` set, exit code 0 and the
  warning; with the test passing, exit code 0 and no output. In a live session the
  owner broke the same test and asked an unrelated question: the hook blocked the
  stop, Claude received the pytest failure, and the next stop went through. The
  throwaway test was then deleted.
- **Rejected:** Blocking every time with no limit (strictest, but can loop); and a
  hook after every file edit (slower, and fails halfway through a multi-file change).
- **Trade-off:** `make check` runs after every turn, including ones that changed
  nothing. Claude can end a turn with failing checks after one blocked attempt, but
  only with a visible warning.
- **Call:** The owner asked for a hook that blocks on failure. The once-per-turn
  limit was Claude's addition, and the owner accepted it after review.

## D29. FastAPI's built-in docs routes are switched off (2026-11-27)
- **Decision:** `create_app()` passes `docs_url=None`, `redoc_url=None` and
  `openapi_url=None`. The routes `/docs`, `/redoc`, `/openapi.json` and
  `/docs/oauth2-redirect` do not exist, locally or in production. A test asserts that
  the app serves exactly the endpoints listed in `SPEC.md`, so a new route cannot
  appear without that list being edited.
- **Why:** `SPEC.md` lists every endpoint. The service has to be public for Telegram
  to reach it, so every extra route is public too, and two of these pages load
  scripts from a third-party CDN. The pages would earn little here: the service has
  one GET with no input and two POSTs that are called by machines.
- **Not the reason:** Secrecy. The repository is public, so the API description
  reveals nothing new.
- **Rejected:** On locally and off in production through a setting: local would then
  differ from production, and it needs one more setting. It can be revisited at
  step 6 if the page is missed. Keeping the routes and adding them to `SPEC.md`: the
  spec would bend to a framework default. Keeping them behind the secret header:
  more code than the page is worth.
- **Trade-off:** No browser page for trying endpoints by hand. Use `curl` or the tests.
- **Call:** Chosen by the owner from four options on 2026-11-27.

## D30. CI runs `make -k check` on every push, with pinned actions (2026-11-27)
- **Decision:** `.github/workflows/ci.yml` runs `make -k check` on a GitHub-hosted
  Linux runner for every push to any branch. Both actions it uses are pinned to a
  full commit hash, taken from a release at least a week old. uv is pinned to
  0.13.8, the version on the development machine. The job sets `UV_LOCKED=1`, gets a
  read-only token that is not left in the checkout, and is stopped after 10 minutes.
- **Why:** The local check and the Stop hook (D28) run on one laptop and can be
  skipped. CI runs the same Makefile target on a clean machine, so the list of gates
  lives in one place and "works on my machine" is tested on every push. A tag such
  as `v7` can be moved to different code after it was reviewed; a commit hash
  cannot. `uv run` normally rewrites a stale `uv.lock` and carries on, which would
  let CI test versions other than the committed ones; `UV_LOCKED=1` turns that into
  a failure.
- **Evidence:** In a fresh clone with no `.venv` and no `.env`,
  `UV_LOCKED=1 make -k check` passed all four gates. After one version bound was
  loosened in that clone's `pyproject.toml`, every gate stopped with "The lockfile
  at `uv.lock` needs to be updated, but `UV_LOCKED=1` was provided", and `uv.lock`
  was left unchanged. setup-uv v10.4.0 was published on 2026-11-20 at 14:06 UTC,
  after the D5 cooldown date, so the workflow uses v10.3.3 (2026-10-28). setup-uv
  publishes no moving `v10` tag. The first run on GitHub, for commit `b591cff`,
  passed every step in 17 seconds:
  https://github.com/guypztos/FirstSeenBot/actions/runs/46005631875
- **Rejected:** One workflow step per gate (clearer on the GitHub page, but a second
  copy of the gate list). A `pull_request` trigger (only needed for pull requests
  from forks, and it runs branch pushes twice). `--locked` in the Makefile (every
  local dependency change would need a separate `uv lock` first). `version: latest`
  for uv (CI could change without a commit). A fixed runner image name (uv supplies
  Python and every tool, so little comes from the image).
- **Trade-off:** The pinned actions and the uv version are updated by hand. Nothing
  checks that the uv version in the workflow still matches the laptop's. A pull
  request from a fork would get no CI run.
- **Call:** The owner approved these choices from a table of eight on 2026-11-27.
