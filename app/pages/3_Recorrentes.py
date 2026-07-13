"""Produtos recorrentes."""

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
from supermercado.persistence.models import Product, RecurringProduct
from supermercado.services.config_service import ConfigService

prepare_page("Recorrentes")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    st.title("Produtos recorrentes")
    schedule = ConfigService(session).get_recurring_schedule()
    st.caption(
        f"Sessão: {auth.email} · Agenda: {', '.join(schedule.weekdays)} às {schedule.time} "
        f"({schedule.timezone})"
    )

    with st.form("add_recurring"):
        name = st.text_input("Nome do produto")
        brand = st.text_input("Marca (opcional)")
        ean = st.text_input("EAN (opcional)")
        qty = st.number_input("Quantidade", min_value=0.0, value=1.0, step=0.1)
        unit = st.selectbox("Unidade", ["l", "ml", "kg", "g", "un"])
        submitted = st.form_submit_button("Adicionar recorrente")
        if submitted and name.strip():
            product = Product(
                name=name.strip(),
                brand=brand.strip() or None,
                ean=ean.strip() or None,
                quantity_value=float(qty),
                quantity_unit=unit,
            )
            session.add(product)
            session.flush()
            session.add(RecurringProduct(product_id=product.id, enabled=True))
            st.success("Produto recorrente adicionado.")
            st.rerun()

    rows = list(
        session.scalars(
            select(RecurringProduct, Product)
            .join(Product, Product.id == RecurringProduct.product_id)
        )
    )
    # scalars with tuple join is awkward; do simpler
    products = list(session.scalars(select(Product)))
    recurring_ids = {
        r.product_id: r
        for r in session.scalars(select(RecurringProduct))
    }
    if not recurring_ids:
        st.info("Sem produtos recorrentes. A agenda em Configurações define quando o job corre.")
    else:
        for p in products:
            if p.id not in recurring_ids:
                continue
            r = recurring_ids[p.id]
            st.write(
                f"- **{p.name}** ({p.brand or 's/ marca'}) · "
                f"{p.quantity_value} {p.quantity_unit} · "
                f"{'activo' if r.enabled else 'pausado'}"
            )
