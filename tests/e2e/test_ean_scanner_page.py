"""E2E: página de consulta expõe scanner EAN."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["SUPERMERCADO_DEV_BYPASS"] = "1"
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "ean_e2e.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SUPERMERCADO_DEV_BYPASS", "1")
    from supermercado.persistence import db as dbmod

    monkeypatch.setattr(dbmod, "get_database_url", lambda: f"sqlite:///{db_path}")


def test_consulta_page_shows_scanner_modes():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(
        str(ROOT / "app" / "pages" / "1_Consulta_Avulsa.py"), default_timeout=30
    )
    at.run()
    assert not at.exception
    # radio Manual/Câmara/Upload
    assert at.radio
    labels = []
    for r in at.radio:
        opts = getattr(r, "options", None) or []
        labels.extend([str(o) for o in opts])
    assert any("Manual" in lb for lb in labels)
    assert any("Câmara" in lb or "Camera" in lb for lb in labels) or any(
        "Upload" in lb for lb in labels
    )
