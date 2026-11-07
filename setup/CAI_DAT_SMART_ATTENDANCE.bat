@echo off
rem ============================================================
rem  Smart Attendance - Bo cai dat 1 lan bam (Windows 10/11 64-bit)
rem  Bam dup vao tep nay. Windows se hoi quyen Administrator -> chon Yes.
rem ============================================================
chcp 65001 >nul
setlocal

rem --- Tu xin quyen Administrator neu chua co ---
net session >nul 2>&1
if errorlevel 1 (
    echo Dang xin quyen Administrator...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set "KQ=%errorlevel%"
echo.
if not "%KQ%"=="0" (
    echo CAI DAT CHUA XONG. Doc dong bao loi o tren, chup man hinh gui giao vien.
) else (
    echo CAI DAT XONG.
)
pause
exit /b %KQ%
