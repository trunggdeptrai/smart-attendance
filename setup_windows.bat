@echo off
setlocal
cd /d "%~dp0"

py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo Khong tim thay Python 3.11.
    echo Cai Python 3.11 x64 tu python.org va bat tuy chon Python Launcher.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo Khong tao duoc .venv. Kiem tra quyen ghi trong thu muc du an.
        exit /b 1
    )
) else (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
    if errorlevel 1 (
        echo .venv hien tai khong dung Python 3.11.
        echo Khong tu dong xoa moi truong cu. Hay doi ten .venv roi chay lai script.
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Khong cap nhat duoc pip. Kiem tra ket noi mang va thu lai.
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Cai dat requirements that bai.
    echo Kiem tra dang dung Python 3.11 64-bit va ket noi mang.
    exit /b 1
)

".venv\Scripts\python.exe" check_environment.py --create-dirs --init-db
if errorlevel 1 (
    echo Kiem tra moi truong that bai. Xem cac dong [ERROR] o tren.
    exit /b 1
)

if not exist ".streamlit\secrets.toml" (
    echo.
    echo Dat tai khoan dang nhap cho ung dung:
    ".venv\Scripts\python.exe" scripts\set_password.py
    if errorlevel 1 (
        echo Chua dat duoc mat khau. Chay lai: .venv\Scripts\python.exe scripts\set_password.py
        exit /b 1
    )
)

echo Cai dat hoan tat. Chay run.bat de mo ung dung va dang nhap.
