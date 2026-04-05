#!/usr/bin/env bash
# scripts/train_model_loop.sh — Daemon script that runs training cycle loop every 60 minutes for 24 hours
#
# Usage:
#   bash scripts/train_model_loop.sh         # run full 24-hour loop
#   bash scripts/train_model_loop.sh --test  # run single cycle for testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/train_loop.log"
TRAIN_SCRIPT="$SCRIPT_DIR/train_classifier.sh"
VALIDATION_CSV="$(python3 -c "import sys; sys.path.insert(0, '.'); from classifier.config import VALIDATION_CSV; print(VALIDATION_CSV)")"

MAX_CYCLES=24
CYCLE_DURATION=60
MAX_HOURS=24
MAX_SECONDS=$((MAX_HOURS * 3600))

SINGLE_CYCLE=false
for arg in "$@"; do
    [ "$arg" = "--test" ] && SINGLE_CYCLE=true
done

PYTHON=python3
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    PYTHON=python3
fi

cd "$PROJECT_DIR"

mkdir -p "$LOG_DIR"

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

log_separator() {
    echo "────────────────────────────────────────────────────────────────" | tee -a "$LOG_FILE"
}

run_pytest() {
    log "Running pytest tests..."
    if [ -d "$PROJECT_DIR/.venv" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi
    if python -m pytest tests/ -v --tb=short 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ Pytest tests passed"
        return 0
    else
        log "⚠️  Pytest tests failed (non-zero exit)"
        return 1
    fi
}

run_validation() {
    if [ -f "$VALIDATION_CSV" ]; then
        log "Running validation set check..."
        local validation_output
        validation_output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from classifier.config import MODEL_PATH, VECTORIZER_PATH, VALIDATION_CSV
from classifier.ml_model import load_model, load_vectorizer
import pandas as pd

model = load_model(MODEL_PATH)
vectorizer = load_vectorizer(VECTORIZER_PATH)
df = pd.read_csv(VALIDATION_CSV)
X = vectorizer.transform(df['subject'].fillna('') + ' ' + df['body'].fillna(''))
predictions = model.predict(X)
correct = (predictions == df['label']).sum()
total = len(df)
accuracy = correct / total * 100 if total > 0 else 0
print(f'Validation accuracy: {accuracy:.2f}% ({correct}/{total})')
" 2>&1)
        log "$validation_output"
    else
        log "No validation data found at $VALIDATION_CSV, skipping validation"
    fi
}

run_cycle() {
    local cycle_num=$1
    local start_time=$2
    local elapsed
    elapsed=$(($(date +%s) - start_time))

    log_separator
    log "🔄 Cycle $cycle_num started (elapsed: $elapsed seconds)"
    log_separator

    local cycle_success=true

    log "Training TF-IDF/NB model..."
    if [ -d "$PROJECT_DIR/.venv" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi
    if bash "$TRAIN_SCRIPT" 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ Model training completed"
    else
        log "⚠️  Model training failed (continuing to next cycle)"
        cycle_success=false
    fi

    log "Running pytest tests..."
    if run_pytest; then
        log "✅ Pytest tests passed"
    else
        log "⚠️  Pytest tests had failures"
    fi

    run_validation

    log "Cycle $cycle_num completed"
    echo "" >> "$LOG_FILE"
}

main() {
    local start_time
    start_time=$(date +%s)
    local cycle=0

    log_separator
    log "🚀 Training loop started at $(date '+%Y-%m-%d %H:%M:%S')"
    log "Max cycles: $MAX_CYCLES, Max duration: ${MAX_HOURS}h"
    log "Log file: $LOG_FILE"
    log_separator
    echo "" >> "$LOG_FILE"

    while true; do
        cycle=$((cycle + 1))

        if $SINGLE_CYCLE; then
            log "Test mode: running single cycle only"
            run_cycle "$cycle" "$start_time"
            log "✅ Test cycle completed successfully"
            break
        fi

        local current_time
        current_time=$(date +%s)
        local elapsed
        elapsed=$((current_time - start_time))

        if [ "$cycle" -gt "$MAX_CYCLES" ]; then
            log "⏹️  Stopping: reached max cycles ($MAX_CYCLES)"
            break
        fi

        if [ "$elapsed" -ge "$MAX_SECONDS" ]; then
            log "⏹️  Stopping: reached max duration (${MAX_HOURS}h)"
            break
        fi

        run_cycle "$cycle" "$start_time"

        local remaining_seconds=$((MAX_SECONDS - elapsed))
        if [ "$remaining_seconds" -lt "$CYCLE_DURATION" ]; then
            log "⏹️  Stopping: less than ${CYCLE_DURATION}min remaining ($remaining_seconds sec)"
            break
        fi

        log "💤 Sleeping for ${CYCLE_DURATION} minutes..."
        sleep "$CYCLE_DURATION"
    done

    log_separator
    local end_time
    end_time=$(date +%s)
    local total_elapsed=$((end_time - start_time))
    local hours=$((total_elapsed / 3600))
    local minutes=$(((total_elapsed % 3600) / 60))
    log "🏁 Training loop finished after $cycle cycles (${hours}h ${minutes}m total)"
    log_separator
}

main "$@"
