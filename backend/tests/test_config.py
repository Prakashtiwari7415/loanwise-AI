from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.config import get_settings, normalize_database_url


def test_normalize_database_url_converts_legacy_postgres_scheme() -> None:
    neon_url = "postgres://neondb_owner:secret@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb"
    normalized = normalize_database_url(neon_url)
    assert normalized is not None
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized


def test_normalize_database_url_preserves_existing_sslmode() -> None:
    neon_url = "postgresql://user:pass@ep-cool-123.neon.tech/db?sslmode=verify-full"
    normalized = normalize_database_url(neon_url)
    assert normalized is not None
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=verify-full" in normalized


def test_normalize_database_url_leaves_local_postgres_without_ssl() -> None:
    local_url = "postgresql://loanwise:pass@localhost:5432/loanwise"
    normalized = normalize_database_url(local_url)
    assert normalized == "postgresql+psycopg://loanwise:pass@localhost:5432/loanwise"


def test_normalize_database_url_leaves_sqlite_unchanged() -> None:
    sqlite_url = "sqlite+pysqlite:///:memory:"
    assert normalize_database_url(sqlite_url) == sqlite_url


def test_normalize_database_url_handles_empty_and_none() -> None:
    assert normalize_database_url(None) is None
    assert normalize_database_url("") is None
    assert normalize_database_url("   ") is None


def test_cors_origins_defaults_in_development() -> None:
    with patch.dict(os.environ, {"ENVIRONMENT": "development", "CORS_ORIGINS": ""}, clear=False):
        settings = get_settings()
        assert "http://localhost:5173" in settings.cors_origins
        assert "http://127.0.0.1:5173" in settings.cors_origins


def test_cors_origins_parses_custom_list() -> None:
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "development", "CORS_ORIGINS": "https://myapp.com, https://preview.myapp.com"},
        clear=False,
    ):
        settings = get_settings()
        assert settings.cors_origins == ("https://myapp.com", "https://preview.myapp.com")


def test_production_rejects_wildcard_cors() -> None:
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": "*"}, clear=False):
        with pytest.raises(ValueError, match="Wildcard CORS origin"):
            get_settings()


def test_production_accepts_explicit_origin() -> None:
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "production", "CORS_ORIGINS": "https://loanwise.onrender.com"},
        clear=False,
    ):
        settings = get_settings()
        assert settings.is_production is True
        assert settings.cors_origins == ("https://loanwise.onrender.com",)
