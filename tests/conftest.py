from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from supermercado.auth.allowlist import SETTINGS_AUTH, ensure_auth_settings
from supermercado.bootstrap import seed_markets
from supermercado.persistence.models import Base
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService

os.environ.setdefault("SUPERMERCADO_DEV_BYPASS", "1")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True)
    session = factory()
    try:
        ConfigService(session).ensure_seeded()
        ensure_auth_settings(ConfigService(session))
        # Bypass para suites locais/CI sem OIDC
        config = ConfigService(session)
        policy = config.get_setting(SETTINGS_AUTH)
        policy["allow_dev_bypass"] = True
        config.set_setting(SETTINGS_AUTH, policy)
        GeoContextService(session).ensure_seeded()
        seed_markets(session)
        yield session
        if session.in_transaction():
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
