#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1
if [ -d ".venv" ]; then source .venv/bin/activate; fi
echo "[dev] Starting uvicorn — http://localhost:8765"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
