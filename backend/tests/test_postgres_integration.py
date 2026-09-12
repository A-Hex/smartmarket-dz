# backend/tests/test_postgres_integration.py
"""
Integration tests against a REAL PostgreSQL database (not the SQLite used by
every other test in this suite).

Why this file exists: every other test runs against in-memory SQLite via the
portable GUID/JSONBType column types, which is fast and needs no external
services -- but SQLite doesn't enforce native ENUM constraints the way
Postgres does. A real bug shipped to production undetected because of this:
SQLAlchemy's `Enum` column type defaults to storing a Python enum member's
`.name` ("OWNER") rather than its `.value` ("owner"), and this mismatch only
surfaces against Postgres's strict native enum type -- SQLite silently
accepted either. Every model's Enum() column now passes `values_callable`
to force `.value` serialization (see app/models/*.py); this file is what
would have caught the bug before it ever reached a real deployment.

These tests are SKIPPED by default (no TEST_POSTGRES_URL set) so the fast
SQLite suite remains the default `pytest` experience. To actually run them:

    createdb smartmarket_test
    export TEST_POSTGRES_URL=postgresql+asyncpg://USER:PASS@localhost:5432/smartmarket_test
    export TEST_POSTGRES_URL_SYNC=postgresql+psycopg2://USER:PASS@localhost:5432/smartmarket_test
    alembic upgrade head   # apply the real migration against the real DB
    pytest tests/test_postgres_integration.py -v

Running this before every deploy (or wiring it into CI with a Postgres
service container) is the actual regression guard for this class of bug --
"all tests pass" was never sufficient proof that this app worked against
production infrastructure, and shouldn't be treated as such going forward.
"""
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app

TEST_POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not TEST_POSTGRES_URL,
    reason=(
        "TEST_POSTGRES_URL not set -- skipping real-Postgres integration tests. "
        "See this file's module docstring to run them for real before deploying."
    ),
)


@pytest_asyncio.fixture
async def pg_client():
    engine = create_async_engine(TEST_POSTGRES_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_against_real_postgres_enum_columns(pg_client: AsyncClient):
    """
    This is the exact scenario that crashed in production: registering a user
    inserts a row with role=UserRole.OWNER into a column backed by a native
    Postgres ENUM type that only permits the lowercase value 'owner'. If
    values_callable regresses, this fails with InvalidTextRepresentationError
    exactly like the original bug did.
    """
    resp = await pg_client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Postgres Integration Test Co",
            "full_name": "PG Tester",
            "email": f"pgtest-{os.getpid()}@integration.dz",
            "password": "PgIntegration1!",
        },
    )
    assert resp.status_code == 201, resp.text
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_after_register_against_real_postgres(pg_client: AsyncClient):
    email = f"pgtest-login-{os.getpid()}@integration.dz"
    reg = await pg_client.post(
        "/api/v1/auth/register",
        json={"company_name": "PG Login Co", "full_name": "PG Login", "email": email, "password": "PgLogin123!"},
    )
    assert reg.status_code == 201, reg.text

    login = await pg_client.post("/api/v1/auth/login", json={"email": email, "password": "PgLogin123!"})
    assert login.status_code == 200, login.text
