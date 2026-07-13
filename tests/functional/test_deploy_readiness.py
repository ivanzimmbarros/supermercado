"""Garantias de prontidão para deploy isolado."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_streamlit_entry_and_deps_exist():
    assert (ROOT / "app" / "Home.py").exists()
    assert (ROOT / "requirements.txt").exists()
    assert (ROOT / "packages.txt").exists()
    assert "libzbar0" in (ROOT / "packages.txt").read_text()
    assert "pyzbar" in (ROOT / "requirements.txt").read_text()
    assert "Pillow" in (ROOT / "requirements.txt").read_text()


def test_secrets_example_and_deploy_doc():
    secrets = ROOT / ".streamlit" / "secrets.toml.example"
    assert secrets.exists()
    text = secrets.read_text()
    assert "[auth]" in text
    assert "allowed_emails" in text
    deploy = (ROOT / "docs" / "DEPLOY.md").read_text()
    assert "anti-impacto" in deploy.lower() or "Isolamento" in deploy or "isolado" in deploy.lower()
    assert "DATABASE_URL" in deploy
    assert "app/Home.py" in deploy
