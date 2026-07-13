"""Funcional: consulta por EAN usa matching idêntico quando possível."""

from __future__ import annotations

from supermercado.matching.engine import ProductRef, score_match
from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery, ProviderStatus
from supermercado.scanning.ean import validate_ean
from supermercado.services.search_service import SearchService


class EanAwareProvider:
    market_id = "continente"

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]:
        ean = query.ean or "5601312508007"
        return [
            Offer(
                market_id=self.market_id,
                external_id="ean-1",
                name="Leite UHT Meio Gordo Continente",
                brand="Continente",
                ean=ean,
                price_final=0.86,
                price_before=None,
                is_promo=False,
                promo_label=None,
                promo_valid_until=None,
                quantity_value=1,
                quantity_unit="l",
                pack_count=1,
                unit_price_text=None,
                available=True,
                availability_label=None,
                url=None,
                image_url=None,
            )
        ]

    def get_by_ean(self, ean: str, geo: GeoQueryContext) -> list[Offer]:
        return self.search(ProductQuery(ean=ean), geo)

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(self.market_id, True, "ok")


def test_search_by_validated_ean(db_session, monkeypatch):
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: [EanAwareProvider()],
    )
    check = validate_ean("5601312508007")
    assert check.ok
    result = SearchService(db_session).search(ean=check.ean)
    assert result.ranked
    assert result.ranked[0].offer.ean == "5601312508007"
    match = score_match(
        ProductRef(name="Leite", ean=check.ean, quantity_value=1, quantity_unit="l"),
        ProductRef(
            name=result.ranked[0].offer.name,
            ean=result.ranked[0].offer.ean,
            quantity_value=1,
            quantity_unit="l",
        ),
    )
    assert match.match_type == "identical"
