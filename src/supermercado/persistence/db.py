from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from supermercado.persistence.models import Base


def get_database_url() -> str:
    """URL da BD via ambiente/secrets — sem host hardcoded de produção."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPERMERCADO_DATABASE_URL")
    if url:
        return url
    # Fallback local/testes apenas (filesystem efémero no Cloud não é target)
    os.makedirs("data/local", exist_ok=True)
    return "sqlite:///data/local/supermercado.db"


def create_db_engine(url: str | None = None) -> Engine:
    db_url = url or get_database_url()
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, future=True, connect_args=connect_args)

    if db_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_db(engine: Engine | None = None) -> Engine:
    engine = engine or create_db_engine()
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    engine = engine or create_db_engine()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
