"""Garantir que o arranque one-click existe para utilizador não técnico."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_start_scripts_exist():
    sh = ROOT / "iniciar_app.sh"
    bat = ROOT / "iniciar_app.bat"
    guide = ROOT / "COMECE_AQUI.md"
    assert sh.exists()
    assert bat.exists()
    assert guide.exists()
    assert os.access(sh, os.X_OK)
    text = sh.read_text(encoding="utf-8")
    assert "streamlit run app/Home.py" in text
    assert "SUPERMERCADO_DEV_BYPASS=1" in text
    assert "supermercado.bootstrap" in text
