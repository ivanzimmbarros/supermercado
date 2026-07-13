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
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from supermercado.bootstrap import bootstrap
from supermercado.persistence.db import create_db_engine, session_scope
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService

st.set_page_config(
    page_title="Supermercado Familiar",
    layout="wide",
)


@st.cache_resource
def _engine():
    return create_db_engine()


def _ensure_runtime():
    bootstrap()
    return _engine()


def main() -> None:
    engine = _ensure_runtime()
    with session_scope(engine) as session:
        geo = GeoContextService(session).ensure_seeded()
        schedule = ConfigService(session).get_recurring_schedule()
        windows = ConfigService(session).get_opportunity_windows_days()
        markets = ConfigService(session).get_enabled_market_ids()

        st.title("Supermercado Familiar")
        st.caption(
            "Listas, consultas e histórico de preços — Continente & Pingo Doce (MVP)."
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Código postal ativo", geo.postal_code)
        c2.metric("Agenda", f"{', '.join(schedule.weekdays)} · {schedule.time}")
        c3.metric("Janelas (dias)", ", ".join(map(str, windows)))

        st.info(
            "Use o menu lateral: **Configurações** para alterar CP, dias/hora do job e demais "
            "parâmetros. Nenhum valor operacional está hardcoded no domínio."
        )
        st.write("Mercados activos:", ", ".join(markets) if markets else "—")
        st.write("Estado do CP:", geo.status, f"({geo.locality or 'localidade n/d'})")


if __name__ == "__main__":
    main()
else:
    main()
