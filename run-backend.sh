#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"

ROOT_VENV="$(dirname "$0")/venv"
if [ -x "$ROOT_VENV/bin/python" ]; then
  source "$ROOT_VENV/bin/activate"
elif [ -x "$(command -v python3.9)" ]; then
  python3.9 -m venv .venv
  source .venv/bin/activate
else
  python3 -m venv .venv 2>/dev/null || true
  source .venv/bin/activate
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
uvicorn main:app --reload --port 8000
