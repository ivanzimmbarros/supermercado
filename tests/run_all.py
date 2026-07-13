"""
Gate obrigatório: corre a suite completa do projecto.

Uso:
  export PYTHONPATH=src SUPERMERCADO_DEV_BYPASS=1
  python3 -m tests.run_all
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("SUPERMERCADO_DEV_BYPASS", "1")


def main() -> int:
    # Respeita pytest.ini (unit/functional/e2e/simulated_users)
    code = pytest.main([])
    if code != 0:
        print(
            "\n[GATE FALHOU] Corrija o código/testes e volte a executar. "
            "Nenhuma etapa pode fechar com falhas.",
            file=sys.stderr,
        )
    else:
        print("\n[GATE OK] Suite completa verde — etapa elegível para fecho.")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
