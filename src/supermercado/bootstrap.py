"""Inicializa schema e seeds operacionais (sem hardcodes em runtime)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from supermercado.defaults_seed import SEED_ENABLED_MARKETS
from supermercado.persistence.db import init_db, session_scope
from supermercado.persistence.models import Market
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService

MARKET_CATALOG = [
    ("continente", "Continente", "continente", 10),
    ("pingo_doce", "Pingo Doce", "pingo_doce", 20),
    ("lidl", "Lidl", "lidl", 30),
    ("intermarche", "Intermarché", "intermarche", 40),
    ("aldi", "Aldi", "aldi", 50),
]


def seed_markets(session: Session) -> None:
    enabled = set(SEED_ENABLED_MARKETS)
    # Se já existir config de mercados, respeitar
    config = ConfigService(session)
    config.ensure_seeded()
    enabled = set(config.get_enabled_market_ids())

    for market_id, name, provider_key, priority in MARKET_CATALOG:
        row = session.get(Market, market_id)
        if row is None:
            session.add(
                Market(
                    id=market_id,
                    name=name,
                    country="PT",
                    enabled=market_id in enabled,
                    provider_key=provider_key,
                    priority=priority,
                )
            )
        else:
            row.enabled = market_id in enabled
            row.provider_key = provider_key
            row.priority = priority
    session.flush()


def bootstrap() -> None:
    engine = init_db()
    with session_scope(engine) as session:
        ConfigService(session).ensure_seeded()
        from supermercado.auth.allowlist import ensure_auth_settings

        ensure_auth_settings(ConfigService(session))
        GeoContextService(session).ensure_seeded()
        seed_markets(session)


if __name__ == "__main__":
    bootstrap()
    print("Bootstrap concluído.")
