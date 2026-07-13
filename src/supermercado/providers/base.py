"""Contrato comum dos price providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass
class ProductQuery:
    text: str | None = None
    ean: str | None = None
    brand: str | None = None
    limit: int = 12


@dataclass
class GeoQueryContext:
    postal_code: str
    locality: str | None = None
    preferred_store_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Offer:
    market_id: str
    external_id: str
    name: str
    brand: str | None
    ean: str | None
    price_final: float
    price_before: float | None
    is_promo: bool
    promo_label: str | None
    promo_valid_until: date | None
    quantity_value: float | None
    quantity_unit: str | None
    pack_count: int
    unit_price_text: str | None
    available: bool
    availability_label: str | None
    url: str | None
    image_url: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderStatus:
    market_id: str
    ok: bool
    message: str
    enabled: bool = True


class PriceProvider(Protocol):
    market_id: str

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]: ...

    def get_by_ean(self, ean: str, geo: GeoQueryContext) -> list[Offer]: ...

    def healthcheck(self) -> ProviderStatus: ...
