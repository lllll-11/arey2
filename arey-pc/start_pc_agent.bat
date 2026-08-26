@echo off
title Arey 2.1 - Agente de Laptop (Prioridad Alta)
color a
echo =======================================================
echo          INICIANDO AGENTE DE LAPTOP - AREY 2.1
echo       (Prioridad Alta & Rendimiento en Tiempo Real)
echo =======================================================
echo.

cd /d "%~dp0"

if not exist venv (
    echo [1/2] Creando entorno virtual de Python...
    python -m venv venv
    echo [2/2] Instalando dependencias iniciales...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
) else (
    call venv\Scripts\activate.bat
)

echo Conectando con el Cerebro Central de Arey con Prioridad Alta...
python client.py

if errorlevel 1 (
    echo.
    echo Ocurrio un error inesperado al cerrar Arey.
    pause
)
