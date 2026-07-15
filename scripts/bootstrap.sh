#!/usr/bin/env bash
set -euo pipefail

# AI-Benchmark developer bootstrap script for Linux / macOS
# Usage: bash scripts/bootstrap.sh

echo "[bootstrap] Bootstrapping AI-Benchmark development environment..."

if [ ! -d ".git" ]; then
    echo "ERROR: Run this script from the repository root."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not found on PATH."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED="3.13"

if [[ "$PYTHON_VERSION" != "$REQUIRED" ]]; then
    echo "WARNING: Expected Python $REQUIRED, found $PYTHON_VERSION. Continuing anyway..."
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "[bootstrap] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[bootstrap] Virtual environment already exists, reusing..."
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "[bootstrap] Upgrading pip..."
pip install --upgrade pip

# Install project with dev extras
echo "[bootstrap] Installing project with dev dependencies..."
pip install -e ".[dev]"

# Copy .env.example if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[bootstrap] Copying .env.example to .env..."
    cp .env.example .env
fi

echo "[bootstrap] Done. Activate your environment with: source .venv/bin/activate"
echo "[bootstrap] Run tests with: pytest aibenchmark/tests/ -q"
