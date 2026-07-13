"""
Roteiros simulados de utilizadores familiares a navegar no sistema.

Ivan e Maria exercitam configuração, consulta e histórico como na vida real.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

os.environ["SUPERMERCADO_DEV_BYPASS"] = "1"

from supermercado.auth.allowlist import SETTINGS_AUTH, ensure_auth_settings, set_allowed_emails
from supermercado.bootstrap import bootstrap, seed_markets
from supermercado.domain.schedule import RecurringScheduleConfig
from supermercado.persistence.models import Base, PriceSnapshot
from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery, ProviderStatus
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService
from supermercado.services.search_service import SearchService

ROOT = Path(__file__).resolve().parents[2]


class FamilyFakeProvider:
    market_id = "pingo_doce"

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]:
        return [
            Offer(
                market_id="pingo_doce",
                external_id="48150",
                name="Leite UHT Meio Gordo",
                brand="Pingo Doce",
                ean=None,
                price_final=0.86,
                price_before=None,
                is_promo=False,
                promo_label=None,
                promo_valid_until=None,
                quantity_value=1,
                quantity_unit="l",
                pack_count=1,
                unit_price_text="1 L | 0,86 €/L",
                available=True,
                availability_label=None,
                url="https://example.test/leite",
                image_url=None,
            )
        ]

    def get_by_ean(self, ean: str, geo: GeoQueryContext) -> list[Offer]:
        return self.search(ProductQuery(ean=ean), geo)

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(self.market_id, True, "ok")


@pytest.fixture()
def family_session(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'family.db'}"
    os.environ["DATABASE_URL"] = db_url
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    ConfigService(session).ensure_seeded()
    ensure_auth_settings(ConfigService(session))
    cfg = ConfigService(session)
    policy = cfg.get_setting(SETTINGS_AUTH)
    policy["allow_dev_bypass"] = True
    cfg.set_setting(SETTINGS_AUTH, policy)
    set_allowed_emails(cfg, ["ivan@gmail.com", "maria@gmail.com"])
    GeoContextService(session).ensure_seeded()
    seed_markets(session)
    session.commit()
    yield session
    session.close()


def test_ivan_changes_postal_and_searches_then_returns(family_session, monkeypatch):
    """Ivan muda de CP, consulta leite, volta ao CP antigo e confirma histórico intacto."""
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: [FamilyFakeProvider()],
    )
    geo = GeoContextService(family_session)
    config = ConfigService(family_session)

    # 1) Confirma seed
    active = geo.ensure_seeded()
    assert active.postal_code == "4815-413"

    # 2) Consulta no CP de Vizela
    r1 = SearchService(family_session).search(text="leite uht")
    assert r1.ranked
    assert r1.ranked[0].offer.available
    snaps_vizela = geo.count_snapshots(active.id)
    assert snaps_vizela >= 1

    # 3) Família muda temporariamente para Lisboa
    lisboa = geo.activate("1000-001", locality="Lisboa", district="Lisboa")
    family_session.refresh(active)
    assert active.status == "frozen"
    assert lisboa.status == "active"

    r2 = SearchService(family_session).search(text="leite uht")
    assert r2.postal_code == "1000-001"
    assert geo.count_snapshots(lisboa.id) >= 1
    assert geo.count_snapshots(active.id) == snaps_vizela  # congelado intacto

    # 4) Regresso a Vizela retoma série
    back = geo.activate("4815-413")
    assert back.id == active.id
    assert geo.count_snapshots(back.id) == snaps_vizela

    # 5) Ivan ajusta agenda para 3x/semana via config (como na UI)
    config.set_recurring_schedule(
        RecurringScheduleConfig(
            enabled=True,
            weekdays=["tue", "thu", "fri"],
            time="07:00",
            timezone="Europe/Lisbon",
            executions_per_week=3,
        )
    )
    assert config.get_recurring_schedule().executions_per_week == 3


def test_maria_navigates_streamlit_home_and_consulta(tmp_path, monkeypatch):
    """Maria abre Home e Consulta avulsa (simulação UI)."""
    from streamlit.testing.v1 import AppTest

    db_path = tmp_path / "maria.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SUPERMERCADO_DEV_BYPASS", "1")

    from supermercado.persistence import db as dbmod

    monkeypatch.setattr(dbmod, "get_database_url", lambda: f"sqlite:///{db_path}")

    home = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30)
    home.run()
    assert not home.exception

    consulta = AppTest.from_file(
        str(ROOT / "app" / "pages" / "1_Consulta_Avulsa.py"), default_timeout=30
    )
    consulta.run()
    assert not consulta.exception
    # Maria preenche produto
    produto = next(i for i in consulta.text_input if "produto" in str(i.label).lower())
    produto.set_value("leite").run()
    assert not consulta.exception
