#!/usr/bin/env bash
set -euo pipefail

echo "[devcontainer] Installing backend dependencies with pip3 (Python 3.11)"
python3 -m pip install --upgrade pip
pip3 install -r backend/requirements.txt

echo "[devcontainer] Setup complete. Try running:"
echo "  cd backend && gunicorn --config gunicorn.conf.py wsgi:application"
