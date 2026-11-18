@echo off
title FUTBora - Stremio/Nuvio Addon
color 0A
echo ===================================================
echo     FUTBora - Addon de Futebol para Stremio/Nuvio
echo ===================================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no PATH!
    echo Instale o Python 3.8+ em https://www.python.org e marque 'Add to PATH'.
    pause
    exit /b
)

echo Iniciando servidor do Addon...
echo URL do Addon: http://localhost:7000/manifest.json
echo.
python server.py
pause
