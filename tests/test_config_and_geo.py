from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from supermercado.domain.schedule import RecurringScheduleConfig
from supermercado.persistence.models import Base, MarketProduct, PriceSnapshot
from supermercado.services.config_service import ConfigService, ScheduleService
from supermercado.services.geo_service import GeoContextService


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True)
    s = factory()
    try:
        yield s
        if s.is_active:
            s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def test_schedule_invariant_days_match_executions():
    with pytest.raises(ValueError):
        RecurringScheduleConfig(
            enabled=True,
            weekdays=["tue", "fri"],
            time="07:00",
            timezone="Europe/Lisbon",
            executions_per_week=3,
        )


def test_seed_schedule_and_should_run_on_tuesday_morning(session: Session):
    config = ConfigService(session)
    config.ensure_seeded()
    schedule = config.get_recurring_schedule()
    assert schedule.weekdays == ["tue", "fri"]
    assert schedule.time == "07:00"
    assert schedule.executions_per_week == 2

    svc = ScheduleService(session, config)
    # Terça 7:05 Lisbon = 6:05 UTC (UTC+1 winter) — use fixed offset via ZoneInfo
    local = datetime(2026, 7, 14, 7, 5, tzinfo=ZoneInfo("Europe/Lisbon"))  # Tue
    now_utc = local.astimezone(ZoneInfo("UTC"))
    decision = svc.should_run_now(now_utc=now_utc, window_minutes=15)
    assert decision.should_run is True

    svc.mark_ran(decision.local_now, decision.schedule)
    again = svc.should_run_now(now_utc=now_utc, window_minutes=15)
    assert again.should_run is False
    assert "já executado" in again.reason


def test_geo_switch_freezes_previous_and_resumes_history(session: Session):
    geo_svc = GeoContextService(session)
    first = geo_svc.ensure_seeded()
    assert first.postal_code == "4815-413"
    assert first.status == "active"

    # Snapshot no primeiro CP
    mp = MarketProduct(
        id="mp1",
        market_id="continente",
        external_id="1",
        name="Leite",
    )
    # Market FK — create minimal market via raw insert without FK enforcement issues:
    # SQLite with models has FK to markets. Create market row.
    from supermercado.persistence.models import Market

    session.add(
        Market(
            id="continente",
            name="Continente",
            enabled=True,
            provider_key="continente",
            priority=10,
        )
    )
    session.add(mp)
    session.flush()
    session.add(
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
    session.flush()
    assert geo_svc.count_snapshots(first.id) == 1

    second = geo_svc.activate("1000-001", locality="Lisboa", district="Lisboa")
    session.refresh(first)
    assert first.status == "frozen"
    assert second.status == "active"
    assert second.postal_code == "1000-001"
    assert geo_svc.count_snapshots(first.id) == 1
    assert geo_svc.count_snapshots(second.id) == 0

    # Snapshot no segundo CP
    session.add(
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
    session.flush()

    # Voltar ao CP original — retoma série antiga
    resumed = geo_svc.activate("4815-413")
    session.refresh(first)
    session.refresh(second)
    assert resumed.id == first.id
    assert resumed.status == "active"
    assert second.status == "frozen"
    assert geo_svc.count_snapshots(resumed.id) == 1
    assert geo_svc.count_snapshots(second.id) == 1

    session.add(
        PriceSnapshot(
            geo_context_id=resumed.id,
            market_product_id=mp.id,
            captured_at=datetime.now(tz=ZoneInfo("UTC")),
            price_final=0.80,
            unit_price_final=0.80,
            unit_basis="l",
            available=True,
            is_promo=True,
            source="test",
        )
    )
    session.flush()
    assert geo_svc.count_snapshots(resumed.id) == 2


def test_config_update_schedule_from_ui_contract(session: Session):
    config = ConfigService(session)
    config.ensure_seeded()
    updated = config.set_recurring_schedule(
        RecurringScheduleConfig(
            enabled=True,
            weekdays=["mon", "wed", "fri"],
            time="08:30",
            timezone="Europe/Lisbon",
            executions_per_week=3,
        )
    )
    assert updated.time == "08:30"
    assert config.get_recurring_schedule().executions_per_week == 3
