@echo off
title Arey - Agente de Laptop (Windows)
echo =======================================================
echo          INICIANDO AGENTE DE LAPTOP - AREY AI
echo =======================================================
echo.

cd /d "%~dp0"

if not exist venv (
    echo Creando entorno virtual de Python...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando / Verificando dependencias...
pip install -r requirements.txt

echo.
echo Conectando con el Cerebro Central de Arey...
python client.py

pause
