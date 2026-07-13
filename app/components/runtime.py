"""Helpers partilhados das páginas Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from supermercado.auth.allowlist import render_login_gate
from supermercado.bootstrap import bootstrap
from supermercado.persistence.db import create_db_engine, session_scope
from supermercado.services.config_service import ConfigService


def prepare_page(title: str):
    st.set_page_config(page_title=title, layout="wide")
    bootstrap()
    engine = create_db_engine()
    return engine


def gated_session(engine):
    """Context manager-like pattern: devolve (session, auth) já passando o gate."""

    class _Ctx:
        def __enter__(self):
            self._cm = session_scope(engine)
            self.session = self._cm.__enter__()
            config = ConfigService(self.session)
            # Em local sem secrets Google: permitir bypass só se allowlist vazia + flag
            # A flag default é False; activamos automaticamente apenas se não há OIDC
            # e existe env SUPERMERCADO_DEV_BYPASS=1
            import os

            from supermercado.auth.allowlist import SETTINGS_AUTH, ensure_auth_settings

            ensure_auth_settings(config)
            if os.environ.get("SUPERMERCADO_DEV_BYPASS") == "1":
                policy = config.get_setting(SETTINGS_AUTH)
                policy["allow_dev_bypass"] = True
                config.set_setting(SETTINGS_AUTH, policy)
            self.auth = render_login_gate(config)
            return self.session, self.auth

        def __exit__(self, exc_type, exc, tb):
            return self._cm.__exit__(exc_type, exc, tb)

    return _Ctx()
