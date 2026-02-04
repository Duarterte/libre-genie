#!/usr/bin/env bash
current_dir="$(pwd)"
cd ../my-postgres-compose || exit 1
sudo docker compose down -v
sudo docker compose up -d
cd "$current_dir" || exit 1
if [ -f "$PWD/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$PWD/.venv/bin/activate"
fi
if [ -x "$PWD/.venv/bin/uvicorn" ]; then
  "$PWD/.venv/bin/uvicorn" server:app --reload --host 0.0.0.0
fi

uvicorn server:app --reload --host 0.0.0.0
