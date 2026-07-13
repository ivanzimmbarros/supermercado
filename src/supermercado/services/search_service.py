"""Orquestra pesquisa multi-mercado, matching e snapshots por geo_context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from supermercado.matching.engine import ProductRef, score_match
from supermercado.normalization.units import compute_unit_price
from supermercado.persistence.models import MarketProduct, PriceSnapshot
from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery
from supermercado.providers.registry import build_providers
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService


@dataclass
class RankedOffer:
    offer: Offer
    unit_price_final: float
    unit_basis: str
    match_type: str
    confidence: float
    unit_factor: float
    market_product_id: str | None = None


@dataclass
class SearchResult:
    query: str
    geo_context_id: str
    postal_code: str
    ranked: list[RankedOffer]
    errors: dict[str, str]


class SearchService:
    def __init__(self, session: Session):
        self.session = session
        self.config = ConfigService(session)
        self.geo = GeoContextService(session)

    def search(
        self,
        text: str | None = None,
        ean: str | None = None,
        limit_per_market: int = 8,
        canonical: ProductRef | None = None,
        persist: bool = True,
    ) -> SearchResult:
        geo = self.geo.ensure_seeded()
        enabled = self.config.get_enabled_market_ids()
        providers = build_providers(enabled)
        query = ProductQuery(text=text, ean=ean, limit=limit_per_market)
        geo_q = GeoQueryContext(postal_code=geo.postal_code, locality=geo.locality)

        all_offers: list[Offer] = []
        errors: dict[str, str] = {}
        for provider in providers:
            try:
                if ean:
                    offers = provider.get_by_ean(ean, geo_q)
                else:
                    offers = provider.search(query, geo_q)
                all_offers.extend(offers)
            except Exception as exc:  # noqa: BLE001
                errors[provider.market_id] = str(exc)

        ref = canonical or ProductRef(
            name=text or ean or "",
            ean=ean,
        )

        ranked: list[RankedOffer] = []
        for offer in all_offers:
            unit = compute_unit_price(
                offer.price_final,
                offer.quantity_value,
                offer.quantity_unit,
                offer.pack_count,
            )
            if unit is None:
                continue
            offer_ref = ProductRef(
                name=offer.name,
                brand=offer.brand,
                ean=offer.ean,
                quantity_value=offer.quantity_value,
                quantity_unit=offer.quantity_unit,
                pack_count=offer.pack_count,
            )
            match = score_match(ref, offer_ref)
            mp_id = None
            if persist:
                mp_id = self._upsert_market_product(offer)
                self._insert_snapshot(
                    geo_context_id=geo.id,
                    market_product_id=mp_id,
                    offer=offer,
                    unit_price_final=unit.unit_price_final,
                    unit_basis=unit.unit_basis,
                )
            ranked.append(
                RankedOffer(
                    offer=offer,
                    unit_price_final=unit.unit_price_final,
                    unit_basis=unit.unit_basis,
                    match_type=match.match_type,
                    confidence=match.confidence,
                    unit_factor=match.unit_factor,
                    market_product_id=mp_id,
                )
            )

        # Ranking: disponíveis primeiro, depois menor €/unidade
        ranked.sort(
            key=lambda r: (
                0 if r.offer.available else 1,
                r.unit_price_final,
                0 if r.match_type == "identical" else 1,
            )
        )
        self.session.flush()
        return SearchResult(
            query=text or ean or "",
            geo_context_id=geo.id,
            postal_code=geo.postal_code,
            ranked=ranked,
            errors=errors,
        )

    def _upsert_market_product(self, offer: Offer) -> str:
        stmt = select(MarketProduct).where(
            MarketProduct.market_id == offer.market_id,
            MarketProduct.external_id == offer.external_id,
        )
        row = self.session.scalars(stmt).first()
        now = datetime.now(tz=ZoneInfo("UTC"))
        if row is None:
            row = MarketProduct(
                market_id=offer.market_id,
                external_id=offer.external_id,
                name=offer.name,
                brand=offer.brand,
                ean=offer.ean,
                quantity_value=offer.quantity_value,
                quantity_unit=offer.quantity_unit,
                pack_count=offer.pack_count,
                url=offer.url,
                image_url=offer.image_url,
                raw_json=offer.raw,
                last_seen_at=now,
            )
            self.session.add(row)
            self.session.flush()
        else:
            row.name = offer.name
            row.brand = offer.brand
            row.ean = offer.ean or row.ean
            row.quantity_value = offer.quantity_value
            row.quantity_unit = offer.quantity_unit
            row.pack_count = offer.pack_count
            row.url = offer.url
            row.raw_json = offer.raw
            row.last_seen_at = now
            self.session.flush()
        return row.id

    def _insert_snapshot(
        self,
        geo_context_id: str,
        market_product_id: str,
        offer: Offer,
        unit_price_final: float,
        unit_basis: str,
    ) -> None:
        self.session.add(
            PriceSnapshot(
                geo_context_id=geo_context_id,
                market_product_id=market_product_id,
                captured_at=datetime.now(tz=ZoneInfo("UTC")),
                price_final=offer.price_final,
                price_before=offer.price_before,
                currency="EUR",
                is_promo=offer.is_promo,
                promo_label=offer.promo_label,
                promo_valid_until=offer.promo_valid_until,
                unit_price_final=unit_price_final,
                unit_basis=unit_basis,
                available=offer.available,
                availability_label=offer.availability_label,
                source="live_query",
            )
        )
