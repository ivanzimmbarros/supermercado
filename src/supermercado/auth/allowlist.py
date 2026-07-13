"""Autenticação Google OIDC + allowlist (sem e-mails hardcoded no domínio)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import streamlit as st

from supermercado.services.config_service import ConfigService

SETTINGS_ALLOWED_EMAILS = "allowed_emails"
SETTINGS_AUTH = "auth_policy"


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    email: str | None
    name: str | None
    reason: str


def load_allowed_emails_from_secrets() -> list[str]:
    """Lê allowlist dos secrets Streamlit / env — nunca hardcoded."""
    emails: list[str] = []
    try:
        raw = st.secrets.get("app", {}).get("allowed_emails", [])
        if isinstance(raw, str):
            emails.extend([e.strip() for e in raw.split(",") if e.strip()])
        elif isinstance(raw, (list, tuple)):
            emails.extend([str(e).strip() for e in raw if str(e).strip()])
    except Exception:
        pass

    env_raw = os.environ.get("ALLOWED_EMAILS", "")
    if env_raw:
        emails.extend([e.strip() for e in env_raw.split(",") if e.strip()])

    # normalizar
    return sorted({e.lower() for e in emails if "@" in e})


def ensure_auth_settings(config: ConfigService) -> None:
    if config._get_raw(SETTINGS_AUTH) is None:
        # allow_dev_bypass só para ambientes sem OIDC configurado
        config.set_setting(
            SETTINGS_AUTH,
            {
                "require_google_login": True,
                "allow_dev_bypass": False,
            },
            changed_by=None,
        )
    if config._get_raw(SETTINGS_ALLOWED_EMAILS) is None:
        # Arranque: secrets/env; UI pode acrescentar depois
        config.set_setting(
            SETTINGS_ALLOWED_EMAILS,
            {"emails": load_allowed_emails_from_secrets()},
            changed_by=None,
        )


def get_allowed_emails(config: ConfigService) -> list[str]:
    ensure_auth_settings(config)
    from_db = [e.lower() for e in config.get_setting(SETTINGS_ALLOWED_EMAILS).get("emails", [])]
    from_secrets = load_allowed_emails_from_secrets()
    return sorted(set(from_db) | set(from_secrets))


def set_allowed_emails(
    config: ConfigService, emails: list[str], changed_by: str | None = None
) -> list[str]:
    cleaned = sorted({e.strip().lower() for e in emails if "@" in e})
    config.set_setting(SETTINGS_ALLOWED_EMAILS, {"emails": cleaned}, changed_by)
    return cleaned


def _google_configured() -> bool:
    try:
        auth = st.secrets.get("auth", {})
        return bool(auth.get("client_id") and auth.get("client_secret"))
    except Exception:
        return False


def _read_streamlit_user() -> tuple[bool, str | None, str | None]:
    user = getattr(st, "user", None)
    if user is None:
        return False, None, None
    is_logged = bool(getattr(user, "is_logged_in", False))
    email = getattr(user, "email", None)
    name = getattr(user, "name", None) or getattr(user, "given_name", None)
    return is_logged, (email.lower() if email else None), name


def require_login(config: ConfigService) -> AuthResult:
    """Gate de autenticação para páginas Streamlit."""
    ensure_auth_settings(config)
    policy = config.get_setting(SETTINGS_AUTH)
    allowed = get_allowed_emails(config)

    logged, email, name = _read_streamlit_user()
    if logged:
        if not allowed:
            return AuthResult(
                False,
                email,
                name,
                "Allowlist vazia. Configure e-mails autorizados em Configurações/secrets.",
            )
        if email not in allowed:
            return AuthResult(False, email, name, "E-mail não autorizado para esta aplicação.")
        return AuthResult(True, email, name, "ok")

    if _google_configured() and policy.get("require_google_login", True):
        st.login("google")
        return AuthResult(False, None, None, "Aguarda login Google")

    # Sem OIDC: bypass apenas se explicitamente permitido na config
    if policy.get("allow_dev_bypass", False):
        return AuthResult(True, "dev@local", "Desenvolvimento", "dev_bypass")

    return AuthResult(
        False,
        None,
        None,
        "Login Google não configurado. Adicione secrets [auth] ou active allow_dev_bypass só em local.",
    )


def render_login_gate(config: ConfigService) -> AuthResult:
    result = require_login(config)
    if result.ok:
        return result
    st.warning(result.reason)
    if result.email and "não autorizado" in result.reason.lower():
        if st.button("Terminar sessão"):
            st.logout()
            st.rerun()
    st.stop()
    return result  # pragma: no cover
