@echo off
REM Arranque local one-click no Windows
cd /d "%~dp0"

echo ============================================
echo   Supermercado Familiar - arranque local
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao encontrado. Instale Python 3 em https://www.python.org/downloads/
  echo Marque a opcao "Add Python to PATH" na instalacao.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo A criar ambiente Python (.venv)...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo A instalar / actualizar dependencias...
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

set PYTHONPATH=src
set SUPERMERCADO_DEV_BYPASS=1

echo A preparar base de dados local...
python -m supermercado.bootstrap

echo.
echo App a iniciar em http://localhost:8501
echo Para parar: feche esta janela ou Ctrl+C.
echo.

streamlit run app/Home.py
pause
