"""
classifier/config.py — All thresholds and settings for the classifier pipeline.

Do NOT hardcode these values anywhere else; import from here.
"""

import json
from pathlib import Path
from typing import Optional

import requests

# ── Directory paths ───────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.parent          # gmail_expense_tracker/
MODELS_DIR = _HERE / "models"
LOGS_DIR   = _HERE / "logs"
DATA_DIR   = _HERE / "data"

MODEL_PATH      = MODELS_DIR / "nb_tfidf_model.joblib"
VECTORIZER_PATH = MODELS_DIR / "vectorizer.joblib"
TRAINING_CSV    = DATA_DIR   / "training_emails.csv"
VALIDATION_CSV  = DATA_DIR   / "validation_emails.csv"
FEEDBACK_CSV    = DATA_DIR   / "feedback.csv"
CACHE_DB        = DATA_DIR   / "cached_predictions.db"
AUDIT_LOG       = LOGS_DIR   / "classification_audit.csv"

# ── Stage 1: Rule engine thresholds ───────────────────────────────────────────
RULE_HIGH_THRESHOLD = 6    # score >= 6 → EXPENSE (high confidence)
RULE_ZERO_THRESHOLD = 0    # score == 0 → NOT_EXPENSE

# ── Stage 2: ML model thresholds ─────────────────────────────────────────────
ML_HIGH_THRESHOLD = 0.85   # probability >= 0.85 → accept ML result
ML_LOW_THRESHOLD  = 0.65   # probability <  0.65 → escalate to LLM (was 0.55)

# ── Stage 3: LLM confidence bands ────────────────────────────────────────────
LLM_ACCEPT_BANDS = ["high", "medium"]   # accept LLM result
LLM_REVIEW_BAND  = "low"                # send to human review

# ── LLM settings (phi4-mini) ──────────────────────────────────────────────────
LLM_MODEL_NAME  = "phi4-mini"
LLM_TEMPERATURE = 0.1
LLM_NUM_PREDICT = 80
PROMPT_VERSION  = "v1"                  # bump when prompt template changes

# ── Stage 3 backend selector ──────────────────────────────────────────────────
# Options: "distilbert" | "phi4-mini"
# Persisted in data/classifier_settings.json (safer than modifying this file).
# distilbert → faster, CPU-only, ~200 ms/email, no Ollama needed
# phi4-mini  → zero-shot, better for ambiguous emails, needs Ollama
_SETTINGS_FILE = DATA_DIR / "classifier_settings.json"

def _load_stage3_backend() -> str:
    try:
        if _SETTINGS_FILE.exists():
            return json.loads(_SETTINGS_FILE.read_text()).get(
                "STAGE3_BACKEND", "distilbert"
            )
    except Exception:
        pass
    return "distilbert"

def save_stage3_backend(backend: str) -> None:
    """Persist the Stage 3 backend choice to data/classifier_settings.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    try:
        if _SETTINGS_FILE.exists():
            existing = json.loads(_SETTINGS_FILE.read_text())
    except Exception:
        pass
    existing["STAGE3_BACKEND"] = backend
    _SETTINGS_FILE.write_text(json.dumps(existing, indent=2))

STAGE3_BACKEND = _load_stage3_backend()

# ── DistilBERT settings ────────────────────────────────────────────────────────
DISTILBERT_BASE_MODEL     = "distilbert-base-uncased"
DISTILBERT_MODEL_DIR      = MODELS_DIR / "distilbert"

# ── Lightweight models settings ────────────────────────────────────────────────
LIGHTWEIGHT_MODEL_DIR     = MODELS_DIR / "lightweight"
DISTILBERT_BASE_DIR       = MODELS_DIR / "distilbert_base"
DISTILBERT_MAX_LENGTH     = 384
DISTILBERT_BATCH_SIZE     = 8
DISTILBERT_EPOCHS         = 3
DISTILBERT_HIGH_THRESHOLD = 0.85
DISTILBERT_LOW_THRESHOLD  = 0.65

# ── Model download config ───────────────────────────────────────────────────────
MODEL_RELEASE_OWNER = "Shivam-20"
MODEL_RELEASE_REPO = "emailExpensesTracker"
MODEL_RELEASE_API = f"https://api.github.com/repos/{MODEL_RELEASE_OWNER}/{MODEL_RELEASE_REPO}/releases/latest"
MODEL_DOWNLOAD_BASE = f"https://github.com/{MODEL_RELEASE_OWNER}/{MODEL_RELEASE_REPO}/releases/download/latest"
CURRENT_MODEL_VERSION = "v1.0"

# Version file
MODEL_VERSION_FILE = DATA_DIR / "model_version.json"


def check_model_exists(model_path: Path) -> bool:
    """Check if model file/directory exists locally."""
    return model_path.exists()


def download_model_from_release(model_name: str, dest_dir: Path) -> bool:
    """Download a model from GitHub release. Returns True if successful."""
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        download_url = f"{MODEL_DOWNLOAD_BASE}/{model_name}"
        dest_path = dest_dir / model_name

        response = requests.get(download_url, timeout=120)
        response.raise_for_status()

        dest_path.write_bytes(response.content)
        return True
    except Exception:
        return False


def check_for_model_updates() -> tuple[bool, str]:
    """Check if newer models available. Returns (update_available, new_version)."""
    try:
        response = requests.get(MODEL_RELEASE_API, timeout=30)
        response.raise_for_status()
        release_data = response.json()
        new_version = release_data.get("tag_name", "")

        if not new_version:
            return False, ""

        local_version = get_local_model_version()
        if local_version and new_version != local_version:
            return True, new_version

        return False, new_version
    except Exception:
        return False, ""


def get_local_model_version() -> str:
    """Get currently installed model version."""
    try:
        if MODEL_VERSION_FILE.exists():
            data = json.loads(MODEL_VERSION_FILE.read_text())
            return data.get("version", "")
    except Exception:
        pass
    return ""
