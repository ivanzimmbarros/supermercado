"""Testes funcionais de comparação de listas."""

from __future__ import annotations

import pytest

from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery, ProviderStatus
from supermercado.services.list_service import ListService


class DualMarketFake:
    def __init__(self, market_id: str, price: float, available: bool = True):
        self.market_id = market_id
        self.price = price
        self.available = available

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]:
        return [
            Offer(
                market_id=self.market_id,
                external_id=f"{self.market_id}-1",
                name=f"Leite UHT {self.market_id}",
                brand=self.market_id,
                ean=None,
                price_final=self.price,
                price_before=None,
                is_promo=False,
                promo_label=None,
                promo_valid_until=None,
                quantity_value=1,
                quantity_unit="l",
                pack_count=1,
                unit_price_text=None,
                available=self.available,
                availability_label=None if self.available else "Indisponível",
                url=None,
                image_url=None,
            )
        ]

    def get_by_ean(self, ean: str, geo: GeoQueryContext) -> list[Offer]:
        return self.search(ProductQuery(ean=ean), geo)

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(self.market_id, True, "ok")


def test_compare_list_picks_cheapest_available(db_session, monkeypatch):
    providers = [
        DualMarketFake("continente", 1.10, available=True),
        DualMarketFake("pingo_doce", 0.86, available=True),
    ]
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: providers,
    )
    svc = ListService(db_session)
    lst = svc.create_list("Cabaz")
    svc.add_item(
        lst.id,
        name="Leite UHT",
        quantity_value=1,
        quantity_unit="l",
        quantity_desired=2,
    )
    compared = svc.compare_list(lst.id)
    assert len(compared.lines) == 1
    best = compared.lines[0].best
    assert best is not None
    assert best.offer.market_id == "pingo_doce"
    assert compared.lines[0].estimated_line_total == pytest.approx(1.72)
    assert compared.estimated_total == pytest.approx(1.72)


def test_compare_list_ignores_unavailable_for_total(db_session, monkeypatch):
    providers = [
        DualMarketFake("continente", 0.50, available=False),
        DualMarketFake("pingo_doce", 0.99, available=True),
    ]
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: providers,
    )
    svc = ListService(db_session)
    lst = svc.create_list("Cabaz2")
    svc.add_item(lst.id, name="Leite", quantity_value=1, quantity_unit="l", quantity_desired=1)
    compared = svc.compare_list(lst.id)
    assert compared.lines[0].best.offer.market_id == "pingo_doce"
    assert compared.estimated_total == pytest.approx(0.99)
