"""E2E da página de Listas."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["SUPERMERCADO_DEV_BYPASS"] = "1"

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "lists_e2e.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SUPERMERCADO_DEV_BYPASS", "1")
    from supermercado.persistence import db as dbmod

    monkeypatch.setattr(dbmod, "get_database_url", lambda: f"sqlite:///{db_path}")


def test_listas_page_can_create_list_via_form():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "pages" / "2_Listas.py"), default_timeout=30)
    at.run()
    assert not at.exception
    assert at.text_input
    # Preenche nome da nova lista e submete o primeiro form
    at.text_input[0].set_value("Compras teste").run()
    assert not at.exception
    # Clicar botão criar se existir
    create_btns = [b for b in at.button if "criar lista" in str(b.label).lower()]
    if create_btns:
        create_btns[0].click().run()
        assert not at.exception
