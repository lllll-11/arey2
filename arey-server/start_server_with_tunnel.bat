@echo off
title Arey AI - Servidor Central en la Nube
echo ==========================================================
echo          INICIANDO SERVIDOR CENTRAL DE AREY AI
echo ==========================================================
echo.

cd /d "%~dp0"

if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo [1/2] Iniciando Servidor FastAPI en segundo plano...
start "Arey FastAPI Server" /min cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Generando enlace seguro en la nube (Cloudflare Tunnel)...
echo.
echo ==========================================================
echo Tu servidor Arey estara disponible para tu celular en:
echo ==========================================================
..\cloudflared.exe tunnel --url http://localhost:8000

pause
