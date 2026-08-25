@echo off
title Arey AI - Ecosistema Completo
echo ==========================================================
echo           INICIANDO ECOSISTEMA COMPLETO DE AREY
echo ==========================================================
echo.
echo [1] Iniciando Cerebro Central en la Nube...
start "Arey Server" cmd /c "cd /d %~dp0arey-server && start_server_with_tunnel.bat"

timeout /t 5 /nobreak >nul

echo [2] Iniciando Agente de Voz de la Laptop (Escuchando 'Arey')...
start "Arey PC Agent" cmd /c "cd /d %~dp0arey-pc && start_pc_agent.bat"

echo.
echo ==========================================================
echo  ✅ Cerebro y Agente de Voz iniciados con exito.
echo  Puedes ver la URL publica en la ventana del Servidor
echo  para pegarla en la app de tu celular Android.
echo ==========================================================
pause
