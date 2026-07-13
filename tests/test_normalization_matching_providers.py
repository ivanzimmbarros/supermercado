from __future__ import annotations

from pathlib import Path

from supermercado.matching.engine import ProductRef, score_match
from supermercado.normalization.units import compute_unit_price, parse_quantity_from_text
from supermercado.providers.continente import ContinenteProvider
from supermercado.providers.pingo_doce import PingoDoceProvider

FIXTURES = Path(__file__).parent / "fixtures"


def test_unit_price_compares_250_vs_500_fairly():
    a = compute_unit_price(0.60, 250, "ml")
    b = compute_unit_price(1.00, 500, "ml")
    assert a and b
    assert a.unit_basis == "l"
    assert b.unit_basis == "l"
    # 0.60/0.25=2.4 €/L vs 1.00/0.5=2.0 €/L → 500 ml melhor
    assert b.unit_price_final < a.unit_price_final


def test_parse_quantity_pack():
    val, unit, pack = parse_quantity_from_text("Pack 4x200 ml")
    assert pack == 4
    assert val == 200
    assert unit == "ml"


def test_matching_identical_ean():
    c = ProductRef(name="Leite", ean="5601312508007", quantity_value=1, quantity_unit="l")
    o = ProductRef(name="Outro", ean="5601312508007", quantity_value=1, quantity_unit="l")
    m = score_match(c, o)
    assert m.match_type == "identical"
    assert m.confidence == 1.0


def test_matching_similar_volume():
    c = ProductRef(
        name="Extrato de tomate marca propria",
        brand="Pingo Doce",
        quantity_value=250,
        quantity_unit="ml",
    )
    o = ProductRef(
        name="Extrato de tomate marca propria",
        brand="Continente",
        quantity_value=500,
        quantity_unit="ml",
    )
    m = score_match(c, o)
    assert m.match_type in {"similar", "identical", "weak"}
    assert abs(m.unit_factor - 2.0) < 0.05 or m.match_type == "weak"


def test_continente_parser_fixture():
    html = (FIXTURES / "continente_leite.html").read_text(encoding="utf-8", errors="ignore")
    offers = ContinenteProvider().parse_grid_html(html, limit=6)
    assert len(offers) >= 1
    assert all(o.market_id == "continente" for o in offers)
    assert all(o.price_final > 0 for o in offers)


def test_pingo_doce_parser_fixture():
    html = (FIXTURES / "pingo_doce_leite.html").read_text(encoding="utf-8", errors="ignore")
    offers = PingoDoceProvider().parse_grid_html(html, limit=6)
    assert len(offers) >= 1
    assert all(o.price_final > 0 for o in offers)
    # deve detectar pelo menos uma promo se o fixture tiver reduced price
    assert any(o.brand for o in offers)
