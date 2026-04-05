# Train Model Loop - 24 Hour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a script that trains TF-IDF/NB classifier every 60 minutes for 24 hours, tests after each cycle with pytest + validation set, and logs results.

**Architecture:** A daemon script that runs a training cycle loop:
1. Train TF-IDF/NB model using `scripts/train_classifier.sh`
2. Run pytest tests to measure accuracy
3. Run validation set check
4. Log results with timestamp
5. Sleep 60 minutes
6. Repeat until 24 hours elapsed

**Tech Stack:** bash, pytest, sklearn (TF-IDF/NB)

---

## File Structure

- Create: `scripts/train_model_loop.sh` - main loop script
- Modify: `scripts/train_classifier.sh` - add timestamp logging
- Log output: `logs/train_loop.log`

---

### Task 1: Create the main training loop script

**Files:**
- Create: `scripts/train_model_loop.sh`
- Test: Manual run (short duration for verification)

- [ ] **Step 1: Write the train_model_loop.sh script**

```bash
#!/usr/bin/env bash
# scripts/train_model_loop.sh — Train TF-IDF/NB model every hour for 24 hours
#
# Usage:
#   bash scripts/train_model_loop.sh        # run full 24h loop
#   bash scripts/train_model_loop.sh --test # run single cycle for testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

LOG_FILE="$PROJECT_DIR/logs/train_loop.log"
TRAINING_SCRIPT="$SCRIPT_DIR/train_classifier.sh"
TOTAL_DURATION=86400      # 24 hours in seconds
CYCLE_INTERVAL=3600       # 60 minutes in seconds
MAX_CYCLES=24

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

run_single_cycle() {
    local cycle_num=$1
    log "========================================"
    log "Starting cycle $cycle_num of $MAX_CYCLES"
    log "========================================"
    
    # Step 1: Train model
    log "Training TF-IDF/NB model..."
    if bash "$TRAINING_SCRIPT" 2>&1 | tee -a "$LOG_FILE"; then
        log "Training completed successfully"
    else
        log "ERROR: Training failed"
        return 1
    fi
    
    # Step 2: Run pytest tests
    log "Running pytest tests..."
    local pytest_output
    if pytest_output=$(cd "$PROJECT_DIR" && pytest tests/test_rules.py tests/test_ml_model.py -v 2>&1); then
        log "Pytest tests passed"
        echo "$pytest_output" >> "$LOG_FILE"
    else
        log "WARNING: Some pytest tests failed"
        echo "$pytest_output" >> "$LOG_FILE"
    fi
    
    # Step 3: Run validation set check (if validation data exists)
    local val_csv="$PROJECT_DIR/data/validation_emails.csv"
    if [ -f "$val_csv" ]; then
        log "Running validation set check..."
        python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from classifier.ml_model import load_model
from classifier.schemas import EmailInput
import pandas as pd

model, vectorizer = load_model()
df = pd.read_csv('$val_csv')
correct = 0
total = len(df)
for _, row in df.iterrows():
    email = EmailInput(subject=row.get('subject', ''), body=row.get('body', ''), sender=row.get('sender', ''))
    import numpy as np
    X = vectorizer.transform([email.subject + ' ' + email.body])
    probs = model.predict_proba(X)[0]
    pred = model.classes_[np.argmax(probs)]
    if pred == row['label']:
        correct += 1
accuracy = correct / total * 100 if total > 0 else 0
print(f'Validation accuracy: {accuracy:.1f}% ({correct}/{total})')
" 2>&1 | tee -a "$LOG_FILE"
    else
        log "No validation set found (data/validation_emails.csv)"
    fi
    
    log "Cycle $cycle_num completed"
}

# Parse arguments
TEST_MODE=false
for arg in "$@"; do
    [ "$arg" = "--test" ] && TEST_MODE=true
done

if $TEST_MODE; then
    log "Test mode: running single cycle only"
    run_single_cycle 1
    exit 0
fi

# Main loop
log "Starting 24-hour training loop (max $MAX_CYCLES cycles, 60 min each)"
log "Log file: $LOG_FILE"

START_TIME=$(date +%s)
CYCLE_NUM=1

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ "$ELAPSED" -ge "$TOTAL_DURATION" ]; then
        log "24 hours elapsed - stopping loop"
        break
    fi
    
    if [ "$CYCLE_NUM" -gt "$MAX_CYCLES" ]; then
        log "Max cycles reached - stopping loop"
        break
    fi
    
    if ! run_single_cycle "$CYCLE_NUM"; then
        log "Cycle failed, continuing to next cycle..."
    fi
    
    log "Sleeping for $CYCLE_INTERVAL seconds..."
    sleep "$CYCLE_INTERVAL"
    
    CYCLE_NUM=$((CYCLE_NUM + 1))
done

log "Training loop completed"
```

- [ ] **Step 2: Make script executable**

Run: `chmod +x scripts/train_model_loop.sh`

- [ ] **Step 3: Create sample validation set**

Create `data/validation_emails.csv` with 50-100 sample emails for validation testing.

```bash
# Run quick test (single cycle)
bash scripts/train_model_loop.sh --test
```

Expected: Script runs training, pytest, and validation check successfully

- [ ] **Step 4: Commit**

```bash
git add scripts/train_model_loop.sh
git commit -m "feat: add 24h training loop script"
```

---

### Task 2: Create validation training data

**Files:**
- Create: `data/validation_emails.csv`
- Modify: (if needed) existing training data scripts

- [ ] **Step 1: Export validation subset from training data**

Run: `python3 -c "
import pandas as pd
df = pd.read_csv('data/training_emails.csv')
# Take 10% as validation, stratified by label
val = df.groupby('label', group_keys=False).apply(lambda x: x.sample(frac=0.1, random_state=42))
train = df.drop(val.index)
val.to_csv('data/validation_emails.csv', index=False)
train.to_csv('data/training_emails.csv', index=False)
print(f'Validation: {len(val)} rows, Training: {len(train)} rows')
"`

- [ ] **Step 2: Commit**

```bash
git add data/validation_emails.csv
git commit -m "feat: add validation set for model testing"
```

---

### Task 3: Test the full 24-hour loop

**Files:**
- No new files

- [ ] **Step 1: Start the 24-hour loop**

Run in background:
```bash
nohup bash scripts/train_model_loop.sh > /dev/null 2>&1 &
echo $!
```

- [ ] **Step 2: Verify loop is running**

Check: `tail logs/train_loop.log`

- [ ] **Step 3: Commit completion**

After 24 hours, commit final results summary.
