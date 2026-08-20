# backend/tests/test_config.py
"""Unit tests for Settings' database URL driver normalization (Render/Heroku/Railway compat)."""
from app.core.config import Settings


def test_render_style_url_gets_asyncpg_driver_for_async_field():
    s = Settings(
        DATABASE_URL="postgres://user:pass@dpg-abc.oregon-postgres.render.com/db",
        DATABASE_URL_SYNC="postgres://user:pass@dpg-abc.oregon-postgres.render.com/db",
    )
    assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@dpg-abc.oregon-postgres.render.com/db"


def test_render_style_url_gets_psycopg2_driver_for_sync_field():
    s = Settings(
        DATABASE_URL="postgres://user:pass@dpg-abc.oregon-postgres.render.com/db",
        DATABASE_URL_SYNC="postgres://user:pass@dpg-abc.oregon-postgres.render.com/db",
    )
    assert s.DATABASE_URL_SYNC == "postgresql+psycopg2://user:pass@dpg-abc.oregon-postgres.render.com/db"


def test_postgresql_scheme_without_driver_also_normalized():
    s = Settings(DATABASE_URL="postgresql://user:pass@host/db", DATABASE_URL_SYNC="postgresql://user:pass@host/db")
    assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@host/db"
    assert s.DATABASE_URL_SYNC == "postgresql+psycopg2://user:pass@host/db"


def test_already_correct_driver_is_left_untouched():
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://smartmarket:smartmarket@postgres:5432/smartmarket",
        DATABASE_URL_SYNC="postgresql+psycopg2://smartmarket:smartmarket@postgres:5432/smartmarket",
    )
    assert s.DATABASE_URL == "postgresql+asyncpg://smartmarket:smartmarket@postgres:5432/smartmarket"
    assert s.DATABASE_URL_SYNC == "postgresql+psycopg2://smartmarket:smartmarket@postgres:5432/smartmarket"


def test_default_settings_unaffected():
    s = Settings()
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert s.DATABASE_URL_SYNC.startswith("postgresql+psycopg2://")
