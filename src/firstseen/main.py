"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory, not a module-level ``app`` object, so that each test builds its own
    instance and importing this module has no side effects (docs/DECISIONS.md, D26).
    """
    # SPEC.md lists every endpoint this service has. FastAPI's built-in pages (/docs,
    # /redoc, /openapi.json) would be extra public routes, so they are switched off
    # (docs/DECISIONS.md, D29).
    app = FastAPI(title="FirstSeen", docs_url=None, redoc_url=None, openapi_url=None)

    # Not "/healthz": Cloud Run reserves some paths ending in "z" and answers them
    # itself with a 404, before the request reaches this app (docs/DECISIONS.md, D27).
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe. Must not touch the database, so it stays cheap and always answers."""
        return {"status": "ok"}

    return app
