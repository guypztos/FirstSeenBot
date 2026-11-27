"""The service exposes only the endpoints listed in SPEC.md (docs/DECISIONS.md, D29)."""

import httpx
import pytest

from firstseen.main import create_app

# Add each endpoint here in the step that builds it:
# /jobs/poll (step 12) and /telegram/webhook (step 13).
SPEC_ENDPOINTS = {"/health"}


def test_app_serves_only_spec_endpoints() -> None:
    served = {getattr(route, "path", None) for route in create_app().routes}

    assert served == SPEC_ENDPOINTS


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"])
async def test_fastapi_docs_pages_are_off(client: httpx.AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 404
