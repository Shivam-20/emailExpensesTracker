#!/usr/bin/env bash
# scripts/train_classifier.sh — Train (or retrain) the email expense classifier
#
# Usage:
#   bash scripts/train_classifier.sh              # train TF-IDF + NB (default)
#   bash scripts/train_classifier.sh --retrain    # merge feedback.csv and retrain NB
#   bash scripts/train_classifier.sh --distilbert         # fine-tune DistilBERT
#   bash scripts/train_classifier.sh --distilbert --retrain  # DistilBERT + feedback

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MODE="train"
USE_DISTILBERT=false
for arg in "$@"; do
    [ "$arg" = "--retrain" ]    && MODE="retrain"
    [ "$arg" = "--distilbert" ] && USE_DISTILBERT=true
done

cd "$PROJECT_DIR"

# Activate venv if present, otherwise use system Python
PYTHON=python3
if [ -d ".venv" ]; then
    source .venv/bin/activate
    PYTHON=python3
    echo "✅  Virtual environment activated"
fi

echo ""

if $USE_DISTILBERT; then
    # Check training data size before DistilBERT fine-tuning
    TRAINING_CSV="$PROJECT_DIR/data/training_emails.csv"
    if [ -f "$TRAINING_CSV" ]; then
        ROW_COUNT=$(tail -n +2 "$TRAINING_CSV" | wc -l)
        if [ "$ROW_COUNT" -lt 300 ]; then
            echo "⚠️  Warning: training_emails.csv has only $ROW_COUNT rows."
            echo "   DistilBERT needs at least 300 labelled examples for reliable fine-tuning."
            echo "   Proceeding may produce a model that classifies everything as one label."
            read -r -p "   Continue anyway? [y/N] " answer
            if [ "${answer,,}" != "y" ]; then
                echo "Aborted."
                exit 0
            fi
        fi
    fi

    if [ "$MODE" = "retrain" ]; then
        echo "🔄  Retraining DistilBERT (merging feedback.csv)..."
        python3 -c "
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
sys.path.insert(0, '.')
from classifier.config import TRAINING_CSV, FEEDBACK_CSV, DISTILBERT_MODEL_DIR
from classifier.distilbert_model import retrain
retrain(TRAINING_CSV, FEEDBACK_CSV, DISTILBERT_MODEL_DIR)
"
    else
        echo "🤖  Fine-tuning DistilBERT on base training data..."
        python3 -c "
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
sys.path.insert(0, '.')
from classifier.config import TRAINING_CSV, DISTILBERT_MODEL_DIR
from classifier.distilbert_model import train
train(TRAINING_CSV, DISTILBERT_MODEL_DIR)
"
    fi
    echo ""
    echo "✅  DistilBERT model saved → models/distilbert/"
else
    if [ "$MODE" = "retrain" ]; then
        echo "🔄  Retraining classifier (merging feedback.csv)..."
        python3 -c "
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
sys.path.insert(0, '.')
from classifier.config import TRAINING_CSV, FEEDBACK_CSV, MODEL_PATH, VECTORIZER_PATH
from classifier.ml_model import retrain
retrain(TRAINING_CSV, FEEDBACK_CSV, MODEL_PATH, VECTORIZER_PATH)
"
    else
        echo "🤖  Training classifier on base training data..."
        python3 -c "
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
sys.path.insert(0, '.')
from classifier.config import TRAINING_CSV, MODEL_PATH, VECTORIZER_PATH
from classifier.ml_model import train
train(TRAINING_CSV, MODEL_PATH, VECTORIZER_PATH)
"
    fi
    echo ""
    echo "✅  Model saved → models/nb_tfidf_model.joblib"
fi
echo ""
