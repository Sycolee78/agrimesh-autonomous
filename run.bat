@echo off
REM AgriMesh Autonomous - Run Script (Windows)
REM Works on any computer with Python 3.9+

cd /d "%~dp0"

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found. Install Python 3.9+ first.
    exit /b 1
)

REM Create venv if not exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

REM Set PYTHONPATH
set PYTHONPATH=%~dp0;%PYTHONPATH%

REM Run Streamlit
echo 🚀 Starting AgriMesh frontend...
echo    Open: http://localhost:8501
streamlit run frontend/app.py --server.headless true
