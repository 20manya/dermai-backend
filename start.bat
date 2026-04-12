@echo off
title DermAI — Starting...
color 0A

echo.
echo  ██████╗ ███████╗██████╗ ███╗   ███╗ █████╗ ██╗
echo  ██╔══██╗██╔════╝██╔══██╗████╗ ████║██╔══██╗██║
echo  ██║  ██║█████╗  ██████╔╝██╔████╔██║███████║██║
echo  ██║  ██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══██║██║
echo  ██████╔╝███████╗██║  ██║██║ ╚═╝ ██║██║  ██║██║
echo  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝
echo.
echo  Emotion-Aware Skincare AI
echo  ─────────────────────────────────────────────────
echo.

REM ── Check Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Download from: https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit
)

REM ── Check Ollama ──────────────────────────────────────────────────────────────
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama not found.
    echo         Download from: https://ollama.com/download
    echo         Install it, then run this file again.
    pause
    exit
)

REM ── Install Python packages if needed ────────────────────────────────────────
echo [1/4] Checking Python packages...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install packages. Check your internet connection.
    pause
    exit
)
echo       Done.

REM ── Pull llama3 model if not already downloaded ───────────────────────────────
echo [2/4] Checking Llama 3 model (4.7GB — only downloads once)...
ollama pull llama3
echo       Done.

REM ── Start Ollama server in background ────────────────────────────────────────
echo [3/4] Starting Ollama server...
start /min cmd /c "ollama serve"
timeout /t 3 /nobreak >nul
echo       Done.

REM ── Start DermAI API server ───────────────────────────────────────────────────
echo [4/4] Starting DermAI API server...
echo.
echo  ─────────────────────────────────────────────────
echo  API running at:  http://localhost:8000
echo  API docs at:     http://localhost:8000/docs
echo  Press Ctrl+C to stop
echo  ─────────────────────────────────────────────────
echo.

uvicorn api_server:app --reload --port 8000 --host 0.0.0.0

pause
