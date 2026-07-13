"""Bypass de teste no Cloud via secrets."""

from __future__ import annotations

import os

from app.components import runtime as runtime_mod


def test_dev_bypass_from_env(monkeypatch):
    monkeypatch.setenv("SUPERMERCADO_DEV_BYPASS", "1")
    assert runtime_mod._dev_bypass_requested() is True
    monkeypatch.delenv("SUPERMERCADO_DEV_BYPASS", raising=False)
    # sem secrets streamlit no contexto pytest → False
    assert runtime_mod._dev_bypass_requested() is False


def test_teste_streamlit_doc_exists():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    doc = root / "docs" / "TESTE_STREAMLIT.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "app/Home.py" in text
    assert "cursor/architecture-design-b771" in text
    assert "dev_bypass" in text
