@echo off
REM Run SLIIT PDP RPA Bot from Terminal
REM This bot connects to the Docker-based orchestrator for self-healing

echo ==========================================
echo SLIIT PDP RPA Bot - Terminal Mode
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo X Error: Python is not installed or not in PATH
    echo Please install Python 3.12+ or add it to your PATH
    exit /b 1
)

echo [OK] Python is available
python --version
echo.

REM Navigate to bot directory
cd /d "%~dp0sliit_pdp_rpa"

REM Check if venv exists, if not create it
if not exist venv (
    echo [*] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
    echo.
)

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

REM Install/update dependencies
echo [*] Installing dependencies...
pip install -q -r requirements.txt --upgrade
if errorlevel 1 (
    echo X Error: Failed to install dependencies
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Install Playwright browsers
echo [*] Installing Playwright browsers...
playwright install chromium
if errorlevel 1 (
    echo X Error: Failed to install Playwright browsers
    exit /b 1
)
echo [OK] Playwright browsers installed
echo.

REM Display configuration info
echo [*] Configuration:
echo    Bot ID: sliit_pdp_rpa_bot
echo    Orchestrator: http://localhost:8000
echo    Config File: config/settings.yml
echo.

REM Run the bot
echo [*] Starting bot...
echo ==========================================
echo.

python src/main.py

REM If we get here, bot exited
echo.
echo ==========================================
echo [!] Bot exited
echo.
pause
