#!/usr/bin/env bash
# scripts/stop.sh — Stop the running Gmail Expense Tracker instance
#
# Usage:
#   bash scripts/stop.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.app.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "ℹ️   No PID file found — app may not be running via start.sh"
    # Fallback: find by process name
    PIDS=$(pgrep -f "python3 main.py" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "    Found running process(es): $PIDS"
        echo -n "    Kill them? [y/N] "
        read -r ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            for pid in $PIDS; do
                kill "$pid" 2>/dev/null && echo "✅  Killed PID $pid" || echo "⚠️   Could not kill $pid"
            done
        fi
    else
        echo "    No matching processes found."
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "🛑  Stopping Gmail Expense Tracker (PID $PID)..."
    kill "$PID"
    # Wait up to 5 s for graceful exit
    for i in $(seq 1 10); do
        sleep 0.5
        kill -0 "$PID" 2>/dev/null || break
    done
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️   Process did not exit — sending SIGKILL..."
        kill -9 "$PID" 2>/dev/null || true
    fi
    echo "✅  Stopped"
else
    echo "ℹ️   Process $PID is not running (stale PID file)"
fi

rm -f "$PID_FILE"
