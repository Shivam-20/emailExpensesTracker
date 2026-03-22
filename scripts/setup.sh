#!/usr/bin/env bash
# scripts/setup.sh — One-time setup for Gmail Expense Tracker
# Run once after cloning/downloading the project.
#
# Usage:
#   cd gmail_expense_tracker
#   bash scripts/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Gmail Expense Tracker — Setup               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_DIR"

# ── Python version check ──────────────────────────────────────────────────────
PYTHON=$(command -v python3 || command -v python)
PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo "✅  Python $PY_VERSION found"
else
    echo "❌  Python 3.10+ required (found $PY_VERSION)"
    exit 1
fi

# ── Virtual environment ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "🔧  Creating virtual environment (.venv)..."
    "$PYTHON" -m venv .venv
else
    echo "✅  Virtual environment already exists"
fi

source .venv/bin/activate
echo "✅  Virtual environment activated"

# ── Python dependencies ───────────────────────────────────────────────────────
echo ""
echo "📦  Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✅  Python dependencies installed"

# ── Required directories ──────────────────────────────────────────────────────
echo ""
echo "📁  Creating required directories..."
mkdir -p data models logs
echo "✅  directories: data/ models/ logs/"

# ── credentials.json check ────────────────────────────────────────────────────
echo ""
if [ -f "credentials.json" ]; then
    echo "✅  credentials.json found"
else
    echo "⚠️   credentials.json NOT found."
    echo "    Download it from Google Cloud Console:"
    echo "    https://console.cloud.google.com/apis/credentials"
    echo "    → OAuth 2.0 Client IDs → Desktop → Download JSON"
    echo "    → Rename to credentials.json → place here"
fi

# ── Train ML classifier ───────────────────────────────────────────────────────
echo ""
if [ -f "models/nb_tfidf_model.joblib" ]; then
    echo "✅  ML model already trained"
else
    echo "🤖  Training email expense classifier (ML model)..."
    python3 -c "
import sys; sys.path.insert(0,'.')
from classifier.config import TRAINING_CSV, MODEL_PATH, VECTORIZER_PATH
from classifier.ml_model import train
train(TRAINING_CSV, MODEL_PATH, VECTORIZER_PATH)
"
    echo "✅  ML model trained → models/nb_tfidf_model.joblib"
fi

# ── DistilBERT tokenizer cache ────────────────────────────────────────────────
echo ""
echo "📥  Caching DistilBERT tokenizer/config (one-time download ~260 MB)..."
python3 -c "
import sys; sys.path.insert(0,'.')
try:
    from transformers import AutoTokenizer
    from classifier.config import DISTILBERT_BASE_MODEL, DISTILBERT_BASE_DIR
    DISTILBERT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(DISTILBERT_BASE_MODEL)
    tok.save_pretrained(str(DISTILBERT_BASE_DIR))
    print('✅  DistilBERT tokenizer cached →', DISTILBERT_BASE_DIR)
except ImportError:
    print('⚠️   transformers not installed — DistilBERT stage unavailable')
except Exception as e:
    print('⚠️   DistilBERT tokenizer download failed (non-fatal):', e)
" || echo "⚠️   DistilBERT tokenizer step failed (non-fatal)"

# ── Ollama / phi4-mini (optional) ────────────────────────────────────────────
echo ""
if command -v ollama &>/dev/null; then
    echo "🦙  Ollama found. Pulling phi4-mini (LLM fallback)..."
    ollama pull phi4-mini && echo "✅  phi4-mini ready" || echo "⚠️   phi4-mini pull failed (non-fatal)"
else
    echo "ℹ️   Ollama not installed — LLM fallback (Stage 3) will be skipped."
    echo "    Install from: https://ollama.com"
    echo "    Then run:     ollama pull phi4-mini"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Setup complete!  Run:  bash scripts/start.sh   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
