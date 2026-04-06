#!/usr/bin/env bash
# scripts/train_classifier.sh — Train (or retrain) the email expense classifier
#
# Usage:
#   bash scripts/train_classifier.sh              # train TF-IDF + NB (default)
#   bash scripts/train_classifier.sh --retrain    # merge feedback.csv and retrain NB
#   bash scripts/train_classifier.sh --distilbert         # fine-tune DistilBERT
#   bash scripts/train_classifier.sh --distilbert --retrain  # DistilBERT + feedback
#   bash scripts/train_classifier.sh --minilm             # train MiniLM-L6-V2
#   bash scripts/train_classifier.sh --tinybert           # train TinyBERT
#   bash scripts/train_classifier.sh --albert             # train ALBERT
#   bash scripts/train_classifier.sh --mobilebert         # train MobileBERT
#   bash scripts/train_classifier.sh --pipeline            # train all active models from pipeline config
#   bash scripts/train_classifier.sh --pipeline --retrain # train active models with feedback

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MODE="train"
USE_DISTILBERT=false
USE_MINILM=false
USE_TINYBERT=false
USE_ALBERT=false
USE_MOBILEBERT=false
USE_PIPELINE=false
for arg in "$@"; do
    [ "$arg" = "--retrain" ]     && MODE="retrain"
    [ "$arg" = "--distilbert" ] && USE_DISTILBERT=true
    [ "$arg" = "--minilm" ]     && USE_MINILM=true
    [ "$arg" = "--tinybert" ]   && USE_TINYBERT=true
    [ "$arg" = "--albert" ]     && USE_ALBERT=true
    [ "$arg" = "--mobilebert" ] && USE_MOBILEBERT=true
    [ "$arg" = "--pipeline" ]   && USE_PIPELINE=true
done

cd "$PROJECT_DIR"

PYTHON=python3
if [ -d ".venv" ]; then
    source .venv/bin/activate
    PYTHON=python3
    echo "✅  Virtual environment activated"
fi

echo ""

_check_training_data() {
    local csv_path="$1"
    local model_name="$2"
    if [ -f "$csv_path" ]; then
        ROW_COUNT=$(tail -n +2 "$csv_path" | wc -l)
        if [ "$ROW_COUNT" -lt 300 ]; then
            echo "⚠️  Warning: $csv_path has only $ROW_COUNT rows."
            echo "   $model_name needs at least 300 labelled examples."
            read -r -p "   Continue anyway? [y/N] " answer
            if [ "${answer,,}" != "y" ]; then
                echo "Aborted."
                exit 0
            fi
        fi
    fi
}

_train_lightweight() {
    local model_type="$1"
    local model_name="$2"
    _check_training_data "$PROJECT_DIR/data/training_emails.csv" "$model_name"
    
    if [ "$MODE" = "retrain" ]; then
        echo "🔄  Retraining $model_name (merging feedback.csv)..."
        python3 -c "
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
sys.path.insert(0, '.')
from pathlib import Path
from classifier.config import TRAINING_CSV, FEEDBACK_CSV, LIGHTWEIGHT_MODEL_DIR
from classifier.lightweight_models import train_model

train_model('$model_type', TRAINING_CSV if not Path(TRAINING_CSV).exists() else TRAINING_CSV, LIGHTWEIGHT_MODEL_DIR)
"
    else
        echo "🤖  Training $model_name..."
        python3 -c "
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
sys.path.insert(0, '.')
from pathlib import Path
from classifier.config import TRAINING_CSV, LIGHTWEIGHT_MODEL_DIR
from classifier.lightweight_models import train_model

train_model('$model_type', TRAINING_CSV, LIGHTWEIGHT_MODEL_DIR)
"
    fi
    echo ""
    echo "✅  $model_name model saved → models/lightweight/$model_type/"
}

if $USE_PIPELINE; then
    PIPELINE_CONFIG="$PROJECT_DIR/data/pipeline_config.json"
    if [ ! -f "$PIPELINE_CONFIG" ]; then
        echo "❌  Pipeline config not found: $PIPELINE_CONFIG"
        exit 1
    fi
    
    echo "📋  Reading pipeline config..."
    ACTIVE_MODELS=$(python3 -c "
import json
with open('$PIPELINE_CONFIG') as f:
    config = json.load(f)
print(' '.join(config.get('active_models', [])))
")
    
    echo "🔧  Active models: $ACTIVE_MODELS"
    echo ""
    
    for model in $ACTIVE_MODELS; do
        case "$model" in
            minilm-l6-v2)
                _train_lightweight "minilm" "MiniLM-L6-V2"
                ;;
            tinybert)
                _train_lightweight "tinybert" "TinyBERT"
                ;;
            albert-base-v2)
                _train_lightweight "albert" "ALBERT"
                ;;
            mobilebert)
                _train_lightweight "mobilebert" "MobileBERT"
                ;;
            distilbert-base-uncased)
                _USE_DISTILBERT=true
                ;;
            tfidf-nb)
                echo "ℹ️  Skipping tfidf-nb (handled by default training)"
                echo ""
                ;;
            *)
                echo "⚠️  Unknown model in pipeline: $model"
                ;;
        esac
    done
    
    if $USE_DISTILBERT; then
        _check_training_data "$PROJECT_DIR/data/training_emails.csv" "DistilBERT"
        
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
    fi
    
elif $USE_MINILM; then
    _train_lightweight "minilm" "MiniLM-L6-V2"
    
elif $USE_TINYBERT; then
    _train_lightweight "tinybert" "TinyBERT"
    
elif $USE_ALBERT; then
    _train_lightweight "albert" "ALBERT"
    
elif $USE_MOBILEBERT; then
    _train_lightweight "mobilebert" "MobileBERT"
    
elif $USE_DISTILBERT; then
    _check_training_data "$PROJECT_DIR/data/training_emails.csv" "DistilBERT"
    
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
