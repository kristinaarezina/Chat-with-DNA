#!/usr/bin/env bash
set -e

# Load .env if present
if [ -f backend/.env ]; then
  export $(grep -v '^#' backend/.env | xargs)
fi

cd backend

# Pick python3.12 or python3.13 — pydantic-core doesn't support 3.14 yet
PYTHON=$(command -v python3.12 || command -v python3.13 || command -v python3)

# Recreate venv if it was built with an incompatible Python
if [ -d .venv ]; then
  VENV_PYTHON=$(.venv/bin/python3 --version 2>&1 | awk '{print $2}')
  if [[ "$VENV_PYTHON" == 3.14* ]]; then
    echo "Removing Python 3.14 venv (incompatible with pydantic-core)..."
    rm -rf .venv
  fi
fi

if [ ! -d .venv ]; then
  $PYTHON -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "🧬 Starting BioReason-lite backend on http://localhost:8000"
echo "   Open frontend/index.html in your browser"
echo ""

uvicorn main:app --reload --port 8000
