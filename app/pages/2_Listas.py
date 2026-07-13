"""Listas de compras — estrutura inicial."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.components.runtime import gated_session, prepare_page
from supermercado.persistence.db import create_db_engine

prepare_page("Listas")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    st.title("Listas de compras")
    st.caption(f"Sessão: {auth.email}")
    st.info(
        "Próxima entrega: criar listas, adicionar produtos e comparar melhor €/unidade por item."
    )
