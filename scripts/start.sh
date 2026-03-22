#!/usr/bin/env bash
# scripts/start.sh — Launch Gmail Expense Tracker
#
# Usage:
#   bash scripts/start.sh
#   bash scripts/start.sh --no-venv    # skip venv activation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.app.pid"
LOG_FILE="$PROJECT_DIR/logs/app.log"

USE_VENV=true
for arg in "$@"; do
    [ "$arg" = "--no-venv" ] && USE_VENV=false
done

cd "$PROJECT_DIR"

# ── Guard: already running? ───────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️   App is already running (PID $OLD_PID)."
        echo "    Run  bash scripts/stop.sh  to stop it first."
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# ── Virtual environment ───────────────────────────────────────────────────────
if $USE_VENV && [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅  Virtual environment activated"
elif $USE_VENV; then
    echo "ℹ️   No .venv found — using system Python"
    echo "    Run  bash scripts/setup.sh  to create it"
fi

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [ ! -f "credentials.json" ]; then
    echo "❌  credentials.json not found."
    echo "    Run  bash scripts/setup.sh  and follow the instructions."
    exit 1
fi

if [ ! -f "models/nb_tfidf_model.joblib" ]; then
    echo "⚠️   ML model not found — running training first..."
    bash "$SCRIPT_DIR/train_classifier.sh"
fi

# ── Launch ────────────────────────────────────────────────────────────────────
mkdir -p logs
echo "🚀  Starting Gmail Expense Tracker..."
echo "    Logs → $LOG_FILE"
echo "    Stop → bash scripts/stop.sh"
echo ""

nohup python3 main.py >> "$LOG_FILE" 2>&1 &
APP_PID=$!
echo "$APP_PID" > "$PID_FILE"
echo "✅  Launched (PID $APP_PID)"
