"""Lazy database setup so deterministic calculations work without a database."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class DatabaseNotConfiguredError(RuntimeError):
    pass


def configure_database(database_url: str) -> None:
    """Configure a SQLAlchemy engine for PostgreSQL or a test SQLite database."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(database_url, **options)
    _session_factory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def database_is_configured() -> bool:
    return _session_factory is not None or get_settings().database_url is not None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = get_settings().database_url
        if database_url is None:
            raise DatabaseNotConfiguredError("DATABASE_URL is not configured")
        configure_database(database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_database() -> None:
    """Release a configured engine; used only by isolated tests."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
