@echo off
REM AI-Benchmark developer bootstrap script for Windows
REM Usage: scripts\bootstrap.bat

echo [bootstrap] Bootstrapping AI-Benchmark development environment...

if not exist ".git" (
    echo ERROR: Run this script from the repository root.
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python is required but not found on PATH.
    exit /b 1
)

REM Create virtual environment
if not exist ".venv" (
    echo [bootstrap] Creating virtual environment...
    python -m venv .venv
) else (
    echo [bootstrap] Virtual environment already exists, reusing...
)

echo [bootstrap] Upgrading pip...
.venv\Scripts\python -m pip install --upgrade pip

echo [bootstrap] Installing project with dev dependencies...
.venv\Scripts\pip install -e ".[dev]"

REM Copy .env.example if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [bootstrap] Copying .env.example to .env...
        copy /Y .env.example .env >nul
    )
)

echo [bootstrap] Done. Activate your environment with: .venv\Scripts\activate.bat
echo [bootstrap] Run tests with: pytest aibenchmark\tests\ -q
pause
