@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "python_embed\python.exe" (
    echo [ERROR] Python embedded environment not found.
    pause
    exit /b 1
)

echo Starting Sage-DLP (Embedded Version)...
python_embed\python.exe -c "import sys; sys.path.insert(0, '.'); from sage_dlp.main import main; main()"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)