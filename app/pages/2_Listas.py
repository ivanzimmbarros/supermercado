"""Listas de compras com comparação de melhor €/unidade por item."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.components.ean_scanner import render_ean_scanner
from app.components.runtime import gated_session, prepare_page
from supermercado.persistence.db import create_db_engine
from supermercado.services.geo_service import GeoContextService
from supermercado.services.list_service import ListService

prepare_page("Listas")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    lists = ListService(session)
    geo = GeoContextService(session).ensure_seeded()

    st.title("Listas de compras")
    st.caption(
        f"Sessão: {auth.email} · CP ativo: {geo.postal_code} · "
        "Ranking por preço final €/unidade (disponíveis primeiro)"
    )

    with st.form("nova_lista"):
        nome_lista = st.text_input("Nome da nova lista", placeholder="ex.: Compras da semana")
        criar = st.form_submit_button("Criar lista")
        if criar:
            try:
                created = lists.create_list(nome_lista)
                st.success(f"Lista criada: {created.name}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    activas = lists.list_active()
    if not activas:
        st.info("Ainda não há listas activas. Crie a primeira acima.")
        st.stop()

    opcoes = {f"{lst.name} ({lst.id[:8]})": lst.id for lst in activas}
    escolha = st.selectbox("Lista activa", options=list(opcoes.keys()))
    list_id = opcoes[escolha]
    current = lists.get(list_id)
    assert current is not None

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Arquivar lista"):
            lists.archive(list_id)
            st.rerun()
    with col_b:
        comparar = st.button("Comparar preços desta lista", type="primary")

    st.subheader("Adicionar produto")
    scanned_ean = render_ean_scanner("lista_item")
    with st.form("add_item"):
        c1, c2 = st.columns(2)
        with c1:
            pname = st.text_input("Nome")
            brand = st.text_input("Marca")
            category = st.text_input("Categoria")
            ean = st.text_input("EAN", value=scanned_ean or "")
        with c2:
            qty_val = st.number_input("Quantidade da embalagem", min_value=0.0, value=1.0)
            qty_unit = st.selectbox("Unidade", ["l", "ml", "kg", "g", "un"])
            pack = st.number_input("Pack (unidades na embalagem)", min_value=1, value=1, step=1)
            desired = st.number_input("Quantidade a comprar", min_value=0.1, value=1.0, step=0.1)
        notes = st.text_input("Notas")
        add = st.form_submit_button("Adicionar à lista")
        if add:
            try:
                lists.add_item(
                    list_id,
                    name=pname,
                    brand=brand or None,
                    category=category or None,
                    quantity_value=float(qty_val) if qty_val else None,
                    quantity_unit=qty_unit,
                    pack_count=int(pack),
                    ean=(ean or scanned_ean or None),
                    quantity_desired=float(desired),
                    notes=notes or None,
                )
                st.success("Produto adicionado.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.subheader("Itens")
    items = lists.items_for(list_id)
    if not items:
        st.write("Lista vazia.")
    else:
        for item, product in items:
            left, right = st.columns([4, 1])
            with left:
                st.write(
                    f"- **{product.name}**"
                    + (f" ({product.brand})" if product.brand else "")
                    + f" · {product.quantity_value or '?'} {product.quantity_unit or ''}"
                    + f" · comprar ×{item.quantity_desired}"
                    + (f" · {lists.selected_offer_label(item)}" if item.selected_market_product_id else "")
                )
            with right:
                if st.button("Remover", key=f"rm_{item.id}"):
                    lists.remove_item(item.id)
                    st.rerun()

    if comparar:
        with st.spinner("A comparar mercados activos..."):
            compared = lists.compare_list(list_id)
        if compared.errors:
            for key, err in compared.errors.items():
                st.warning(f"{key}: {err}")
        rows = []
        for line in compared.lines:
            best = line.best
            rows.append(
                {
                    "Produto": line.product.name,
                    "Marca": line.product.brand or "",
                    "Qtd": line.item.quantity_desired,
                    "Melhor mercado": best.offer.market_id if best else "—",
                    "Oferta": best.offer.name if best else "—",
                    "Preço emb. €": round(best.offer.price_final, 2) if best else None,
                    "€/unidade": round(best.unit_price_final, 3) if best else None,
                    "Base": best.unit_basis if best else "",
                    "Promo": ("SIM" if best and best.offer.is_promo else "não"),
                    "Stock": (
                        "OK"
                        if best and best.offer.available
                        else ("INDISPONÍVEL" if best else "—")
                    ),
                    "Match": best.match_type if best else "",
                    "Est. linha €": (
                        round(line.estimated_line_total, 2)
                        if line.estimated_line_total is not None
                        else None
                    ),
                }
            )
        st.dataframe(rows, use_container_width=True)
        st.success(f"Total estimado (só itens disponíveis): {compared.estimated_total:.2f} €")
        st.caption(
            "Comparação no âmbito do código postal activo; snapshots gravados no histórico desse CP."
        )
