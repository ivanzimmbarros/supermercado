#!/usr/bin/env bash
# Arranque local one-click — não requer conhecimento técnico.
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================"
echo "  Supermercado Familiar — arranque local"
echo "============================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERRO: Python 3 não encontrado. Instale Python 3 e volte a tentar."
  exit 1
fi

# Dependência do scanner (Linux); ignora se sem permissões/sudo
if command -v apt-get >/dev/null 2>&1; then
  if ! ldconfig -p 2>/dev/null | grep -q libzbar; then
    echo "A tentar instalar libzbar0 (scanner de códigos)..."
    sudo apt-get update -qq && sudo apt-get install -y -qq libzbar0 || \
      echo "Aviso: não foi possível instalar libzbar0. O resto da app funciona; scanner por imagem pode falhar."
  fi
fi

if [ ! -d ".venv" ]; then
  echo "A criar ambiente Python (.venv)..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "A instalar / actualizar dependências..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

export PYTHONPATH=src
export SUPERMERCADO_DEV_BYPASS=1

echo "A preparar base de dados local..."
python -m supermercado.bootstrap

echo ""
echo "App a iniciar em http://localhost:8501"
echo "No menu lateral: Consulta, Listas, Histórico, Recorrentes, Configurações."
echo "Para parar: Ctrl+C neste terminal."
echo ""

exec streamlit run app/Home.py --server.headless true
