"""Ivan usa o scanner (manual + imagem gerada) antes de consultar."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pytest

os.environ["SUPERMERCADO_DEV_BYPASS"] = "1"

from supermercado.scanning.ean import decode_ean_from_bytes, validate_ean
from supermercado.services.list_service import ListService

ROOT = Path(__file__).resolve().parents[2]


def test_ivan_scans_barcode_image_then_adds_to_list(db_session):
    pytest.importorskip("barcode")
    pytest.importorskip("pyzbar")
    from barcode import EAN13
    from barcode.writer import ImageWriter

    buf = BytesIO()
    EAN13("560131250800", writer=ImageWriter()).write(buf)
    scanned = decode_ean_from_bytes(buf.getvalue())
    assert scanned.ok
    assert validate_ean(scanned.ean).ok

    svc = ListService(db_session)
    lista = svc.create_list("Compras com scanner")
    item = svc.add_item(
        lista.id,
        name="Leite via EAN",
        ean=scanned.ean,
        quantity_value=1,
        quantity_unit="l",
        quantity_desired=1,
    )
    products = svc.items_for(lista.id)
    assert products[0][1].ean == "5601312508007"
    assert item.product_id == products[0][0].product_id


def test_ivan_opens_consulta_with_scanner_ui(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    db_path = tmp_path / "ivan_scan.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SUPERMERCADO_DEV_BYPASS", "1")
    from supermercado.persistence import db as dbmod

    monkeypatch.setattr(dbmod, "get_database_url", lambda: f"sqlite:///{db_path}")

    at = AppTest.from_file(
        str(ROOT / "app" / "pages" / "1_Consulta_Avulsa.py"), default_timeout=30
    )
    at.run()
    assert not at.exception
    # Introduz EAN manualmente no modo default
    manuals = [i for i in at.text_input if "ean" in str(i.label).lower()]
    assert manuals
    manuals[0].set_value("5601312508007").run()
    assert not at.exception
