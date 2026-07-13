"""Oportunidades históricas por geo_context e janelas configuráveis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from supermercado.persistence.models import MarketProduct, PriceSnapshot
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService


@dataclass
class OpportunityWindow:
    days: int
    best_unit_price: float | None
    market_id: str | None
    is_promo: bool | None
    captured_at: datetime | None
    available_only: bool = True


class OpportunityService:
    def __init__(self, session: Session):
        self.session = session
        self.config = ConfigService(session)
        self.geo = GeoContextService(session)

    def best_for_market_product(
        self,
        market_product_id: str,
        geo_context_id: str | None = None,
        available_only: bool = True,
    ) -> list[OpportunityWindow]:
        geo_id = geo_context_id or self.geo.ensure_seeded().id
        windows = self.config.get_opportunity_windows_days()
        now = datetime.now(tz=ZoneInfo("UTC"))
        results: list[OpportunityWindow] = []
        for days in windows:
            since = now - timedelta(days=days)
            stmt = select(PriceSnapshot).where(
                PriceSnapshot.geo_context_id == geo_id,
                PriceSnapshot.market_product_id == market_product_id,
                PriceSnapshot.captured_at >= since,
            )
            if available_only:
                stmt = stmt.where(PriceSnapshot.available.is_(True))
            rows = list(self.session.scalars(stmt))
            if not rows:
                results.append(OpportunityWindow(days, None, None, None, None, available_only))
                continue
            best = min(rows, key=lambda r: r.unit_price_final)
            mp = self.session.get(MarketProduct, market_product_id)
            results.append(
                OpportunityWindow(
                    days=days,
                    best_unit_price=best.unit_price_final,
                    market_id=mp.market_id if mp else None,
                    is_promo=best.is_promo,
                    captured_at=best.captured_at,
                    available_only=available_only,
                )
            )
        return results
