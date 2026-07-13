"""Provider Continente (SFCC Search-UpdateGrid)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from supermercado.normalization.units import parse_quantity_from_text
from supermercado.providers.base import (
    GeoQueryContext,
    Offer,
    ProductQuery,
    ProviderStatus,
)

BASE_URL = "https://www.continente.pt"
SEARCH_GRID = (
    "/on/demandware.store/Sites-continente-Site/default/Search-UpdateGrid"
)


def _parse_euro(text: str | None) -> float | None:
    if not text:
        return None
    # Ex.: "6 ,54€" ou "1,09€"
    cleaned = text.replace("\xa0", " ").replace(" ", "")
    m = re.search(r"(\d+),(\d{2})", cleaned)
    if not m:
        m = re.search(r"(\d+)\.(\d{2})", cleaned)
        if not m:
            return None
        return float(f"{m.group(1)}.{m.group(2)}")
    return float(f"{m.group(1)}.{m.group(2)}")


class ContinenteProvider:
    market_id = "continente"

    def __init__(self, timeout: float = 25.0, client: httpx.Client | None = None):
        self.timeout = timeout
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client:
            return self._client
        return httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "pt-PT,pt;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
            },
            follow_redirects=True,
        )

    def healthcheck(self) -> ProviderStatus:
        try:
            with self._http() as client:
                r = client.get(BASE_URL)
            return ProviderStatus(self.market_id, r.status_code < 400, f"HTTP {r.status_code}")
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus(self.market_id, False, str(exc))

    def get_by_ean(self, ean: str, geo: GeoQueryContext) -> list[Offer]:
        return self.search(ProductQuery(text=ean, ean=ean), geo)

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]:
        q = (query.ean or query.text or "").strip()
        if not q:
            return []
        params = {
            "q": q,
            "pmin": "0.01",
            "start": "0",
            "sz": str(min(max(query.limit, 1), 24)),
        }
        # geo/loja: enviar postal como contexto extra quando o site cooperar
        cookies: dict[str, str] = {}
        if geo.postal_code:
            cookies["postalCode"] = geo.postal_code
        url = urljoin(BASE_URL, SEARCH_GRID)
        owned = self._client is None
        client = self._http()
        try:
            response = client.get(url, params=params, cookies=cookies)
            response.raise_for_status()
            return self.parse_grid_html(response.text, limit=query.limit)
        finally:
            if owned:
                client.close()

    def parse_grid_html(self, html: str, limit: int = 12) -> list[Offer]:
        soup = BeautifulSoup(html, "lxml")
        offers: list[Offer] = []
        seen: set[str] = set()
        for tile in soup.select("div.product"):
            pid = tile.get("data-pid")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            name_el = tile.select_one(".pwc-tile--description, a.pwc-tile--description")
            name = name_el.get_text(" ", strip=True) if name_el else None
            if not name:
                continue
            href = None
            if name_el and name_el.name == "a":
                href = name_el.get("href")
            elif tile.select_one("a[href]"):
                href = tile.select_one("a[href]").get("href")
            if href and href.startswith("/"):
                href = urljoin(BASE_URL, href)

            text = tile.get_text(" ", strip=True)
            available = "indispon" not in text.lower()
            badges = [
                b.get_text(" ", strip=True)
                for b in tile.select(
                    ".ct-product-tile-badge, .col-product-tile-badge, .dual-badge-message-text"
                )
            ]
            promo_badges = [b for b in badges if b and b.lower() != "indisponível"]
            is_promo = any("%" in b or "promo" in b.lower() for b in promo_badges)

            price_el = tile.select_one(".pwc-tile--price-primary, .js-product-price")
            price_text = price_el.get_text(" ", strip=True) if price_el else text
            # PVPR / preço antes
            before = None
            pvpr_m = re.search(r"PVPR\s*([\d\s,]+)\s*€", price_text, re.I)
            if pvpr_m:
                before = _parse_euro(pvpr_m.group(1) + "€")
            prices = re.findall(r"(\d+\s*,\s*\d{2})\s*€", price_text)
            parsed_prices = [_parse_euro(p + "€") for p in prices]
            parsed_prices = [p for p in parsed_prices if p is not None]
            price_final = None
            if before and len(parsed_prices) >= 2:
                # tipicamente PVPR depois preço atual
                candidates = [p for p in parsed_prices if abs(p - before) > 0.001]
                price_final = candidates[0] if candidates else parsed_prices[-1]
            elif parsed_prices:
                price_final = parsed_prices[0] if not before else (
                    parsed_prices[1] if len(parsed_prices) > 1 else parsed_prices[0]
                )
            if price_final is None:
                continue

            pack_text = ""
            emb = tile.select_one(".pwc-tile--quantity, .ct-tile-quantity, .pwc-tile")
            # quantidade no snippet "emb. 1 lt" / "emb. 6 x 1 lt"
            m_emb = re.search(r"emb\.\s*([^I]{0,40})", text, re.I)
            if m_emb:
                pack_text = m_emb.group(1)
            qty_val, qty_unit, pack_count = parse_quantity_from_text(pack_text or text)

            brand = None
            # nome costuma terminar com marca
            parts = name.rsplit(" ", 1)
            if len(parts) == 2 and len(parts[1]) > 2:
                brand = parts[1]

            offers.append(
                Offer(
                    market_id=self.market_id,
                    external_id=str(pid),
                    name=name,
                    brand=brand,
                    ean=None,
                    price_final=price_final,
                    price_before=before,
                    is_promo=is_promo or before is not None,
                    promo_label=promo_badges[0] if promo_badges else None,
                    promo_valid_until=None,
                    quantity_value=qty_val,
                    quantity_unit=qty_unit,
                    pack_count=pack_count,
                    unit_price_text=None,
                    available=available,
                    availability_label=None if available else "Indisponível",
                    url=href,
                    image_url=None,
                    raw={"badges": badges, "price_text": price_text, "geo_hint": True},
                )
            )
            if len(offers) >= limit:
                break
        return offers
