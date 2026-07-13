from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from supermercado.domain.schedule import RecurringScheduleConfig
from supermercado.matching.engine import ProductRef, score_match
from supermercado.normalization.units import compute_unit_price, parse_quantity_from_text
from supermercado.providers.continente import ContinenteProvider
from supermercado.providers.pingo_doce import PingoDoceProvider
from supermercado.services.config_service import ConfigService, ScheduleService
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_schedule_invariant_days_match_executions():
    with pytest.raises(ValueError):
        RecurringScheduleConfig(
            enabled=True,
            weekdays=["tue", "fri"],
            time="07:00",
            timezone="Europe/Lisbon",
            executions_per_week=3,
        )


def test_unit_price_compares_250_vs_500_fairly():
    a = compute_unit_price(0.60, 250, "ml")
    b = compute_unit_price(1.00, 500, "ml")
    assert a and b and b.unit_price_final < a.unit_price_final


def test_parse_quantity_pack():
    val, unit, pack = parse_quantity_from_text("Pack 4x200 ml")
    assert (val, unit, pack) == (200.0, "ml", 4)


def test_matching_identical_ean():
    c = ProductRef(name="Leite", ean="5601312508007", quantity_value=1, quantity_unit="l")
    o = ProductRef(name="Outro", ean="5601312508007", quantity_value=1, quantity_unit="l")
    assert score_match(c, o).match_type == "identical"


def test_matching_similar_volume_private_label():
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
    assert all(o.price_final > 0 for o in offers)


def test_pingo_doce_parser_fixture():
    html = (FIXTURES / "pingo_doce_leite.html").read_text(encoding="utf-8", errors="ignore")
    offers = PingoDoceProvider().parse_grid_html(html, limit=6)
    assert len(offers) >= 1


def test_seed_schedule_tuesday_window(db_session):
    config = ConfigService(db_session)
    schedule = config.get_recurring_schedule()
    assert schedule.weekdays == ["tue", "fri"]
    assert schedule.time == "07:00"
    svc = ScheduleService(db_session, config)
    local = datetime(2026, 7, 14, 7, 5, tzinfo=ZoneInfo("Europe/Lisbon"))
    decision = svc.should_run_now(now_utc=local.astimezone(ZoneInfo("UTC")))
    assert decision.should_run is True
    svc.mark_ran(decision.local_now, decision.schedule)
    again = svc.should_run_now(now_utc=local.astimezone(ZoneInfo("UTC")))
    assert again.should_run is False
