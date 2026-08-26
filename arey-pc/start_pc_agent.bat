@echo off
title Arey 2.1 - Agente de Laptop (Prioridad Alta)
color 0b
echo =======================================================
echo          INICIANDO AGENTE DE LAPTOP - AREY 2.1
echo       (Prioridad Alta y Rendimiento en Tiempo Real)
echo =======================================================
echo.

cd /d "%~dp0"

echo [1/3] Limpiando instancias previas de Arey...
powershell -NoProfile -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*client.py*' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

if not exist venv (
    echo [2/3] Creando entorno virtual de Python...
    python -m venv venv
    echo [3/3] Instalando dependencias iniciales...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
) else (
    call venv\Scripts\activate.bat
)

echo [Listo] Conectando con el Cerebro Central de Arey con Prioridad Alta...
python client.py

if errorlevel 1 (
    echo.
    echo Ocurrio un error inesperado al cerrar Arey.
    pause
)
