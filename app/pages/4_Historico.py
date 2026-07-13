"""Histórico e oportunidades por código postal."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.components.runtime import gated_session, prepare_page
from supermercado.persistence.db import create_db_engine
from supermercado.persistence.models import MarketProduct, PriceSnapshot
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService
from supermercado.services.opportunity_service import OpportunityService

prepare_page("Histórico")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    geo_svc = GeoContextService(session)
    active = geo_svc.ensure_seeded()
    geos = geo_svc.list_all()
    windows = ConfigService(session).get_opportunity_windows_days()

    st.title("Histórico e oportunidades")
    st.caption(f"Sessão: {auth.email}")

    options = {f"{g.postal_code} ({g.status})": g.id for g in geos}
    label = st.selectbox(
        "Código postal da série histórica",
        options=list(options.keys()),
        index=list(options.values()).index(active.id) if active.id in options.values() else 0,
    )
    geo_id = options[label]

    snaps = list(
        session.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.geo_context_id == geo_id)
            .order_by(PriceSnapshot.captured_at.desc())
            .limit(100)
        )
    )
    st.write(f"Últimos {len(snaps)} snapshots · janelas configuradas: {windows}")

    if not snaps:
        st.info("Ainda sem histórico para este código postal.")
    else:
        rows = []
        for s in snaps:
            mp = session.get(MarketProduct, s.market_product_id)
            rows.append(
                {
                    "Quando": s.captured_at.isoformat(sep=" ", timespec="minutes"),
                    "Mercado": mp.market_id if mp else "",
                    "Produto": mp.name if mp else s.market_product_id,
                    "Preço €": s.price_final,
                    "€/un": round(s.unit_price_final, 3),
                    "Base": s.unit_basis,
                    "Promo": "SIM" if s.is_promo else "não",
                    "Stock": "OK" if s.available else "NÃO",
                    "Fonte": s.source,
                }
            )
        st.dataframe(rows, use_container_width=True)

        st.subheader("Melhor oportunidade por produto (janelas)")
        # Top market products distinct recent
        seen: set[str] = set()
        opp = OpportunityService(session)
        for s in snaps:
            if s.market_product_id in seen:
                continue
            seen.add(s.market_product_id)
            mp = session.get(MarketProduct, s.market_product_id)
            windows_data = opp.best_for_market_product(s.market_product_id, geo_context_id=geo_id)
            bits = []
            for w in windows_data:
                if w.best_unit_price is None:
                    bits.append(f"{w.days}d: —")
                else:
                    promo = " promo" if w.is_promo else ""
                    bits.append(f"{w.days}d: {w.best_unit_price:.3f}€{promo}")
            st.write(f"**{mp.name if mp else s.market_product_id}** — " + " | ".join(bits))
            if len(seen) >= 15:
                break
