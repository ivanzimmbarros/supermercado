from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from supermercado.bootstrap import seed_markets
from supermercado.persistence.models import Base, PriceSnapshot
from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery, ProviderStatus
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService
from supermercado.services.search_service import SearchService


class FakeProvider:
    market_id = "continente"

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]:
        return [
            Offer(
                market_id="continente",
                external_id="1",
                name="Leite UHT Meio Gordo Continente",
                brand="Continente",
                ean=None,
                price_final=0.86,
                price_before=None,
                is_promo=False,
                promo_label=None,
                promo_valid_until=None,
                quantity_value=1,
                quantity_unit="l",
                pack_count=1,
                unit_price_text="0,86€/lt",
                available=True,
                availability_label=None,
                url="https://example.test/1",
                image_url=None,
            ),
            Offer(
                market_id="continente",
                external_id="2",
                name="Leite UHT Meio Gordo Mimosa",
                brand="Mimosa",
                ean=None,
                price_final=0.90,
                price_before=1.00,
                is_promo=True,
                promo_label="10%",
                promo_valid_until=None,
                quantity_value=1,
                quantity_unit="l",
                pack_count=1,
                unit_price_text=None,
                available=False,
                availability_label="Indisponível",
                url=None,
                image_url=None,
            ),
        ]

    def get_by_ean(self, ean: str, geo: GeoQueryContext) -> list[Offer]:
        return self.search(ProductQuery(ean=ean), geo)

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(self.market_id, True, "ok")


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True)
    s = factory()
    try:
        ConfigService(s).ensure_seeded()
        GeoContextService(s).ensure_seeded()
        seed_markets(s)
        yield s
        if s.is_active:
            s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def test_search_persists_snapshots_on_active_geo(session: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: [FakeProvider()],
    )
    result = SearchService(session).search(text="leite")
    assert result.postal_code == "4815-413"
    assert len(result.ranked) == 2
    # disponível primeiro
    assert result.ranked[0].offer.available is True
    assert result.ranked[0].unit_price_final == pytest.approx(0.86)

    snaps = list(session.scalars(select(PriceSnapshot)))
    assert len(snaps) == 2
    assert all(s.geo_context_id == result.geo_context_id for s in snaps)
    assert any(s.is_promo for s in snaps)
