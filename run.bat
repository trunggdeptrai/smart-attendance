@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua co moi truong .venv.
    echo Chay setup_windows.bat de cai dat Python packages truoc.
    exit /b 1
)

".venv\Scripts\python.exe" check_environment.py
if errorlevel 1 (
    echo.
    echo Kiem tra that bai. Hay xem huong dan trong INSTALL_WINDOWS.md.
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run "%~dp0app.py"
if errorlevel 1 exit /b 1
