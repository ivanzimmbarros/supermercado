"""Consulta avulsa multi-mercado com ranking por €/unidade."""

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
from supermercado.services.geo_service import GeoContextService
from supermercado.services.search_service import SearchService

prepare_page("Consulta avulsa")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    geo = GeoContextService(session).ensure_seeded()
    st.title("Consulta avulsa")
    st.caption(
        f"CP ativo: {geo.postal_code} · Ranking pelo preço final €/unidade · "
        f"Sessão: {auth.email}"
    )

    with st.form("search_form"):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            query = st.text_input("Produto", placeholder="ex.: leite uht meio gordo")
        with col_b:
            ean = st.text_input("EAN (opcional)", placeholder="código de barras")
        submitted = st.form_submit_button("Comparar preços", type="primary")

    if submitted:
        if not query.strip() and not ean.strip():
            st.error("Indique um produto ou EAN.")
        else:
            with st.spinner("A consultar mercados activos..."):
                result = SearchService(session).search(
                    text=query.strip() or None,
                    ean=ean.strip() or None,
                )
            if result.errors:
                for market, err in result.errors.items():
                    st.warning(f"{market}: {err}")

            if not result.ranked:
                st.info("Sem resultados.")
            else:
                best_avail = next((r for r in result.ranked if r.offer.available), None)
                if best_avail:
                    st.success(
                        f"Melhor oportunidade disponível: **{best_avail.offer.name}** em "
                        f"**{best_avail.offer.market_id}** — "
                        f"{best_avail.unit_price_final:.3f} €/{best_avail.unit_basis}"
                        + (" · PROMO" if best_avail.offer.is_promo else "")
                    )

                rows = []
                for r in result.ranked:
                    o = r.offer
                    rows.append(
                        {
                            "Mercado": o.market_id,
                            "Produto": o.name,
                            "Marca": o.brand or "",
                            "Preço €": round(o.price_final, 2),
                            "Antes €": round(o.price_before, 2) if o.price_before else None,
                            "€/unidade": round(r.unit_price_final, 3),
                            "Base": r.unit_basis,
                            "Promo": "SIM" if o.is_promo else "não",
                            "Stock": "OK" if o.available else "INDISPONÍVEL",
                            "Match": r.match_type,
                            "Confiança": round(r.confidence, 2),
                        }
                    )
                st.dataframe(rows, use_container_width=True)
                st.caption(
                    f"Snapshots gravados no histórico do CP {result.postal_code} "
                    f"(geo `{result.geo_context_id}`)."
                )
