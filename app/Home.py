"""
App Streamlit — Comparador familiar de supermercados (PT).
Isolado de qualquer outro projeto Git/Streamlit do autor.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.components.runtime import gated_session, prepare_page
from supermercado.persistence.db import create_db_engine
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService

prepare_page("Supermercado Familiar")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    geo = GeoContextService(session).ensure_seeded()
    schedule = ConfigService(session).get_recurring_schedule()
    windows = ConfigService(session).get_opportunity_windows_days()
    markets = ConfigService(session).get_enabled_market_ids()

    st.title("Supermercado Familiar")
    st.caption("Listas, consultas e histórico de preços — Continente & Pingo Doce (MVP).")
    st.caption(f"Sessão: {auth.name or auth.email}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Código postal ativo", geo.postal_code)
    c2.metric("Agenda", f"{', '.join(schedule.weekdays)} · {schedule.time}")
    c3.metric("Janelas (dias)", ", ".join(map(str, windows)))

    st.info(
        "Use o menu lateral para consultar preços, gerir listas e alterar configurações. "
        "Referências operacionais (CP, agenda, mercados) não estão hardcoded."
    )
    st.write("Mercados activos:", ", ".join(markets) if markets else "—")
    st.write("Estado do CP:", geo.status, f"({geo.locality or 'localidade n/d'})")
