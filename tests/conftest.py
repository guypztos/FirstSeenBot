"""Fixtures shared by every test module. pytest loads this file automatically."""

from collections.abc import AsyncIterator

import httpx
import pytest

from firstseen.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio only.

    anyio's pytest plugin can also run each test on trio. The app runs on asyncio
    (uvicorn now, SQLAlchemy later), so that is the only event loop worth testing.
    """
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """An HTTP client wired straight to a fresh app instance.

    ASGITransport calls the app in-process: no socket is opened and no server runs.
    The code after ``yield`` is the teardown, so the client is closed after each test.
    """
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
