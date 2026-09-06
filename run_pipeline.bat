@echo off
chcp 65001 > nul
title Fotos Backup Workflow
cd /d "%~dp0"

echo ========================================================
echo   Iniciando Fotos Backup Workflow...
echo ========================================================

python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ocorreu um erro durante a execucao.
    pause
)
