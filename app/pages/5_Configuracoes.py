"""Página de configuração — única porta para alterar referências operacionais."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from supermercado.bootstrap import bootstrap, seed_markets
from supermercado.defaults_seed import ALL_WEEKDAYS, WEEKDAY_LABELS_PT
from supermercado.domain.schedule import RecurringScheduleConfig
from supermercado.persistence.db import create_db_engine, session_scope
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService

st.set_page_config(page_title="Configurações", layout="wide")
bootstrap()
engine = create_db_engine()

st.title("Configurações")
st.caption("Tudo o que é referência operacional (CP, agenda, janelas, mercados) altera-se aqui.")

with session_scope(engine) as session:
    config = ConfigService(session)
    geo_svc = GeoContextService(session)
    active = geo_svc.ensure_seeded()
    schedule = config.get_recurring_schedule()
    windows = config.get_opportunity_windows_days()
    markets = config.get_enabled_market_ids()
    all_geos = geo_svc.list_all()

    st.subheader("Código postal")
    st.write(
        f"Ativo: **{active.postal_code}** ({active.locality or '—'}, {active.district or '—'})"
    )
    with st.form("form_postal"):
        new_cp = st.text_input("Novo código postal (NNNN-NNN)", value=active.postal_code)
        locality = st.text_input("Localidade", value=active.locality or "")
        district = st.text_input("Distrito", value=active.district or "")
        submitted_cp = st.form_submit_button("Ativar código postal")
        if submitted_cp:
            try:
                previous_id = active.id
                previous_cp = active.postal_code
                updated = geo_svc.activate(
                    new_cp, locality=locality or None, district=district or None
                )
                if updated.postal_code != previous_cp:
                    st.success(
                        f"CP {previous_cp} congelado. "
                        f"Ativo agora: {updated.postal_code}. "
                        "Históricos anteriores preservados."
                    )
                else:
                    st.success("Código postal ativo atualizado.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.markdown("#### Históricos por código postal")
    for g in all_geos:
        count = geo_svc.count_snapshots(g.id)
        badge = "🟢 ativo" if g.status == "active" else "❄️ congelado"
        st.write(f"- `{g.postal_code}` — {badge} — {count} snapshots — {g.locality or ''}")

    st.divider()
    st.subheader("Agenda dos produtos recorrentes")
    with st.form("form_schedule"):
        enabled = st.checkbox("Agenda ativa", value=schedule.enabled)
        executions = st.number_input(
            "Quantidade de execuções por semana",
            min_value=0,
            max_value=7,
            value=int(schedule.executions_per_week),
            step=1,
        )
        default_days = schedule.weekdays
        chosen_days = st.multiselect(
            "Dias da semana",
            options=ALL_WEEKDAYS,
            default=default_days,
            format_func=lambda d: WEEKDAY_LABELS_PT.get(d, d),
        )
        time_value = st.text_input("Hora padrão (HH:MM)", value=schedule.time)
        timezone = st.text_input("Timezone", value=schedule.timezone)
        submitted_sched = st.form_submit_button("Guardar agenda")
        if submitted_sched:
            try:
                if int(executions) != len(chosen_days):
                    raise ValueError(
                        "A quantidade de execuções deve ser igual ao número de dias "
                        f"selecionados ({len(chosen_days)})."
                    )
                new_schedule = RecurringScheduleConfig(
                    enabled=enabled,
                    weekdays=chosen_days,
                    time=time_value,
                    timezone=timezone,
                    executions_per_week=int(executions),
                )
                config.set_recurring_schedule(new_schedule)
                st.success("Agenda guardada.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.divider()
    st.subheader("Janelas de oportunidade (dias)")
    with st.form("form_windows"):
        raw = st.text_input(
            "Janelas em dias (separadas por vírgula)",
            value=", ".join(map(str, windows)),
        )
        submitted_w = st.form_submit_button("Guardar janelas")
        if submitted_w:
            try:
                days = [int(x.strip()) for x in raw.split(",") if x.strip()]
                config.set_opportunity_windows_days(days)
                st.success("Janelas guardadas.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.divider()
    st.subheader("Mercados ativos")
    catalog = ["continente", "pingo_doce", "lidl", "intermarche", "aldi"]
    with st.form("form_markets"):
        selected = st.multiselect("Mercados habilitados", options=catalog, default=markets)
        submitted_m = st.form_submit_button("Guardar mercados")
        if submitted_m:
            config.set_enabled_market_ids(selected)
            seed_markets(session)
            st.success("Mercados atualizados.")
            st.rerun()
