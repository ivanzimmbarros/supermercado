"""Provider Pingo Doce (SFCC Search-UpdateGrid)."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from supermercado.normalization.units import parse_quantity_from_text
from supermercado.providers.base import (
    GeoQueryContext,
    Offer,
    ProductQuery,
    ProviderStatus,
)

BASE_URL = "https://www.pingodoce.pt"
SEARCH_GRID = (
    "/on/demandware.store/Sites-pingo-doce-Site/default/Search-UpdateGrid"
)


def _parse_euro(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"(\d+),(\d{2})", text.replace("\xa0", " "))
    if not m:
        return None
    return float(f"{m.group(1)}.{m.group(2)}")


class PingoDoceProvider:
    market_id = "pingo_doce"

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
        params = {"q": q, "start": "0", "sz": str(min(max(query.limit, 1), 24))}
        url = urljoin(BASE_URL, SEARCH_GRID)
        owned = self._client is None
        client = self._http()
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return self.parse_grid_html(response.text, limit=query.limit)
        finally:
            if owned:
                client.close()

    def parse_grid_html(self, html: str, limit: int = 12) -> list[Offer]:
        soup = BeautifulSoup(html, "lxml")
        offers: list[Offer] = []
        for brand_el in soup.select(".product-brand-name"):
            root = brand_el
            best = None
            for _ in range(12):
                root = root.parent
                if root is None:
                    break
                if root.select_one(".sales") and root.select_one(".product-unit"):
                    best = root
                    break
            if not best:
                continue
            text = best.get_text(" ", strip=True)
            brand = brand_el.get_text(strip=True)
            unit_text = best.select_one(".product-unit").get_text(strip=True)
            sales = best.select_one(".sales")
            price_final = _parse_euro(sales.get_text() if sales else "")
            if price_final is None:
                continue
            before = None
            m_before = re.search(r"Price reduced from\s*([0-9]+,[0-9]{2})", text)
            if m_before:
                before = _parse_euro(m_before.group(1) + "€")
            is_promo = "promo" in text.lower() or before is not None
            promo_until = None
            m_until = re.search(r"Promo[cç][aã]o at[eé]\s*(\d{2})/(\d{2})", text, re.I)
            if m_until:
                day, month = int(m_until.group(1)), int(m_until.group(2))
                year = datetime.now().year
                try:
                    promo_until = datetime(year, month, day).date()
                except ValueError:
                    promo_until = None

            # nome: texto sem marca/unidade/preços
            name = text
            for cut in [unit_text, "Adicionar", "Quantidade", brand]:
                if cut and cut in name:
                    name = name.split(cut)[0]
            name = re.sub(r"[0-9]+,[0-9]{2}\s*€", "", name)
            name = re.sub(r"Price reduced from.*", "", name, flags=re.I)
            name = name.strip() or brand

            qty_val, qty_unit, pack_count = parse_quantity_from_text(unit_text)
            a = best.select_one("a[href]")
            href = a.get("href") if a else None
            if href and href.startswith("/"):
                href = urljoin(BASE_URL, href)

            # external id do URL se possível
            external_id = href or name
            m_id = re.search(r"-(\d+)\.html", href or "")
            if m_id:
                external_id = m_id.group(1)

            available = not any(
                x in text.lower() for x in ("esgotado", "indispon", "sem stock")
            )

            offers.append(
                Offer(
                    market_id=self.market_id,
                    external_id=str(external_id),
                    name=name,
                    brand=brand,
                    ean=None,
                    price_final=price_final,
                    price_before=before,
                    is_promo=is_promo,
                    promo_label=("Promoção" if is_promo else None),
                    promo_valid_until=promo_until,
                    quantity_value=qty_val,
                    quantity_unit=qty_unit,
                    pack_count=pack_count,
                    unit_price_text=unit_text,
                    available=available,
                    availability_label=None if available else "Indisponível",
                    url=href,
                    image_url=None,
                    raw={"unit_text": unit_text},
                )
            )
            if len(offers) >= limit:
                break
        return offers
