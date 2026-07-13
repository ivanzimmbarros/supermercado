"""Roteiro Maria: cria lista familiar, adiciona itens e compara preços."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["SUPERMERCADO_DEV_BYPASS"] = "1"

from supermercado.providers.base import GeoQueryContext, Offer, ProductQuery, ProviderStatus
from supermercado.services.list_service import ListService

ROOT = Path(__file__).resolve().parents[2]


class CheapPD:
    market_id = "pingo_doce"

    def search(self, query: ProductQuery, geo: GeoQueryContext) -> list[Offer]:
        price = 0.85 if "leite" in (query.text or "").lower() else 1.20
        return [
            Offer(
                market_id=self.market_id,
                external_id="pd-x",
                name=query.text or "produto",
                brand="Pingo Doce",
                ean=None,
                price_final=price,
                price_before=None,
                is_promo=False,
                promo_label=None,
                promo_valid_until=None,
                quantity_value=1,
                quantity_unit="l" if "leite" in (query.text or "").lower() else "un",
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


def test_maria_builds_weekly_list_and_compares(db_session, monkeypatch):
    monkeypatch.setattr(
        "supermercado.services.search_service.build_providers",
        lambda _enabled: [CheapPD()],
    )
    svc = ListService(db_session)

    # Maria cria a lista da semana
    lista = svc.create_list("Compras da semana")
    svc.add_item(
        lista.id,
        name="Leite UHT meio gordo",
        brand="Pingo Doce",
        quantity_value=1,
        quantity_unit="l",
        quantity_desired=3,
    )
    svc.add_item(
        lista.id,
        name="Detergente Loiça",
        quantity_value=1,
        quantity_unit="un",
        quantity_desired=1,
    )

    compared = svc.compare_list(lista.id)
    assert len(compared.lines) == 2
    assert all(line.best is not None for line in compared.lines)
    assert compared.estimated_total == pytest.approx(0.85 * 3 + 1.20)
    # selecção persistida nos itens
    items = svc.items_for(lista.id)
    assert all(item.selected_market_product_id for item, _ in items)


def test_maria_opens_listas_page(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    db_path = tmp_path / "maria_listas.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SUPERMERCADO_DEV_BYPASS", "1")
    from supermercado.persistence import db as dbmod

    monkeypatch.setattr(dbmod, "get_database_url", lambda: f"sqlite:///{db_path}")

    at = AppTest.from_file(str(ROOT / "app" / "pages" / "2_Listas.py"), default_timeout=30)
    at.run()
    assert not at.exception
    titles = [str(t.value) for t in at.title]
    assert any("Listas" in t for t in titles)
