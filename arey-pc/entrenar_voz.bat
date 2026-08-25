@echo off
title Arey - Calibrador y Entrenamiento de Voz
color 0b
echo ===================================================
echo     🎙️ ENTRENAMIENTO DE VOZ PERSONALIZADO - AREY
echo ===================================================
echo.
cd /d "%~dp0"

if not exist venv (
    echo [ERROR] Entorno virtual no encontrado.
    pause
    exit /b
)

echo Iniciando calibrador de microfono y entrenamiento...
echo.
venv\Scripts\python.exe train_voice.py

echo.
echo Presiona cualquier tecla para salir...
pause >nul
