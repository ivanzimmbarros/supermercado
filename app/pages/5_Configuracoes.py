"""Página de configuração — única porta para alterar referências operacionais."""

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
from supermercado.auth.allowlist import (
    SETTINGS_AUTH,
    get_allowed_emails,
    set_allowed_emails,
)
from supermercado.bootstrap import seed_markets
from supermercado.defaults_seed import ALL_WEEKDAYS, WEEKDAY_LABELS_PT
from supermercado.domain.schedule import RecurringScheduleConfig
from supermercado.persistence.db import create_db_engine
from supermercado.services.config_service import ConfigService
from supermercado.services.geo_service import GeoContextService

prepare_page("Configurações")
engine = create_db_engine()

with gated_session(engine) as (session, auth):
    config = ConfigService(session)
    geo_svc = GeoContextService(session)
    active = geo_svc.ensure_seeded()
    schedule = config.get_recurring_schedule()
    windows = config.get_opportunity_windows_days()
    markets = config.get_enabled_market_ids()
    all_geos = geo_svc.list_all()

    st.title("Configurações")
    st.caption(
        "Tudo o que é referência operacional (CP, agenda, janelas, mercados, allowlist) altera-se aqui."
    )
    st.caption(f"Sessão: {auth.email}")

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
                previous_cp = active.postal_code
                updated = geo_svc.activate(
                    new_cp, locality=locality or None, district=district or None
                )
                if updated.postal_code != previous_cp:
                    st.success(
                        f"CP {previous_cp} congelado. Ativo agora: {updated.postal_code}. "
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
        badge = "ativo" if g.status == "active" else "congelado"
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
        chosen_days = st.multiselect(
            "Dias da semana",
            options=ALL_WEEKDAYS,
            default=schedule.weekdays,
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

    st.divider()
    st.subheader("Acesso (allowlist + política)")
    allowed = get_allowed_emails(config)
    policy = config.get_setting(SETTINGS_AUTH)
    with st.form("form_auth"):
        emails_raw = st.text_area(
            "E-mails autorizados (um por linha)",
            value="\n".join(allowed),
        )
        require_google = st.checkbox(
            "Exigir login Google", value=bool(policy.get("require_google_login", True))
        )
        allow_bypass = st.checkbox(
            "Permitir bypass local de desenvolvimento",
            value=bool(policy.get("allow_dev_bypass", False)),
            help="Só para ambiente local sem secrets OIDC. Não usar em produção.",
        )
        submitted_a = st.form_submit_button("Guardar acesso")
        if submitted_a:
            emails = [ln.strip() for ln in emails_raw.splitlines() if ln.strip()]
            set_allowed_emails(config, emails, changed_by=None)
            config.set_setting(
                SETTINGS_AUTH,
                {
                    "require_google_login": require_google,
                    "allow_dev_bypass": allow_bypass,
                },
            )
            st.success("Política de acesso guardada.")
            st.rerun()
