from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from supermercado.domain.schedule import RecurringScheduleConfig
from supermercado.persistence.models import Market, MarketProduct, PriceSnapshot
from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery, ProviderStatus
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService
from supermercado.services.opportunity_service import OpportunityService
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


def test_geo_switch_freezes_and_resumes_history(db_session):
    geo_svc = GeoContextService(db_session)
    first = geo_svc.ensure_seeded()
    assert first.postal_code == "4815-413"

    if db_session.get(Market, "continente") is None:
        db_session.add(
            Market(
                id="continente",
                name="Continente",
                enabled=True,
                provider_key="continente",
                priority=10,
            )
        )
    mp = MarketProduct(id="mp1", market_id="continente", external_id="1", name="Leite")
    db_session.add(mp)
    db_session.flush()
    db_session.add(
        PriceSnapshot(
            geo_context_id=first.id,
            market_product_id=mp.id,
            captured_at=datetime.now(tz=ZoneInfo("UTC")),
            price_final=0.86,
            unit_price_final=0.86,
            unit_basis="l",
            available=True,
            source="test",
        )
    )
    db_session.flush()

    second = geo_svc.activate("1000-001", locality="Lisboa", district="Lisboa")
    db_session.refresh(first)
    assert first.status == "frozen"
    assert second.status == "active"
    assert geo_svc.count_snapshots(first.id) == 1
    assert geo_svc.count_snapshots(second.id) == 0

    db_session.add(
        PriceSnapshot(
            geo_context_id=second.id,
            market_product_id=mp.id,
            captured_at=datetime.now(tz=ZoneInfo("UTC")),
            price_final=0.99,
            unit_price_final=0.99,
            unit_basis="l",
            available=True,
            source="test",
        )
    )
    db_session.flush()

    resumed = geo_svc.activate("4815-413")
    db_session.refresh(second)
    assert resumed.id == first.id
    assert resumed.status == "active"
    assert second.status == "frozen"
    assert geo_svc.count_snapshots(resumed.id) == 1
    assert geo_svc.count_snapshots(second.id) == 1


def test_search_persists_snapshots_on_active_geo(db_session, monkeypatch):
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: [FakeProvider()],
    )
    result = SearchService(db_session).search(text="leite")
    assert result.postal_code == "4815-413"
    assert result.ranked[0].offer.available is True
    snaps = list(db_session.scalars(select(PriceSnapshot)))
    assert len(snaps) == 2
    assert any(s.is_promo for s in snaps)


def test_opportunity_windows_scoped_to_geo(db_session, monkeypatch):
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: [FakeProvider()],
    )
    result = SearchService(db_session).search(text="leite")
    mp_id = result.ranked[0].market_product_id
    assert mp_id
    windows = OpportunityService(db_session).best_for_market_product(mp_id)
    assert [w.days for w in windows] == ConfigService(db_session).get_opportunity_windows_days()
    assert windows[0].best_unit_price is not None


def test_config_update_schedule_contract(db_session):
    config = ConfigService(db_session)
    updated = config.set_recurring_schedule(
        RecurringScheduleConfig(
            enabled=True,
            weekdays=["mon", "wed", "fri"],
            time="08:30",
            timezone="Europe/Lisbon",
            executions_per_week=3,
        )
    )
    assert updated.executions_per_week == 3
    assert config.get_recurring_schedule().time == "08:30"
