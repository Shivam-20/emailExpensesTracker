"""
classifier/category_classifier.py — Stage 4: Category classifier for emails.

Trains on labeled email data to classify into 12 expense categories.
Uses MiniLM embeddings (sentence-transformers) + LogisticRegression.

Public API:
    predict_category(subject, body, sender) -> dict
    train_category_model(csv_path, model_dir)
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CATEGORIES = [
    "EXPENSE",
    "INCOME",
    "INVESTMENT",
    "BILLS",
    "JOB",
    "NEWS",
    "SOCIAL",
    "IMPORTANT",
    "PROMOTIONS",
    "PERSONAL",
    "ORDERS",
    "ACCOUNT",
]

_has_deps = True
try:
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    logger.warning("Missing dependency for category classifier: %s", e)
    _has_deps = False


def train_category_model(csv_path: Path, model_dir: Path) -> None:
    """Train category classifier using MiniLM embeddings + LogisticRegression."""
    if not _has_deps:
        raise ImportError(
            "Required: sentence-transformers, scikit-learn, pandas, joblib"
        )

    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    required = {"subject", "body", "sender", "category"}
    if not required.issubset(df.columns):
        raise ValueError(f"{csv_path} must have columns: {required}")

    df = df.dropna(subset=["subject", "category"])
    df = df[df["category"].isin(CATEGORIES)]

    logger.info("Training category model on %d samples", len(df))

    texts = (
        df["subject"].fillna("")
        + " [SEP] "
        + df["sender"].fillna("")
        + " [SEP] "
        + df["body"].fillna("").str[:2000]
    ).tolist()

    logger.info("Loading MiniLM embedding model...")
    encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    logger.info("Encoding %d texts...", len(texts))
    embeddings = encoder.encode(texts, show_progress_bar=True)

    X = np.array(embeddings)
    y = df["category"].tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = LogisticRegression(
        max_iter=2000,
        C=1.0,
        class_weight="balanced",
        random_state=42,
        solver="lbfgs",
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=CATEGORIES)
    logger.info("Eval report:\n%s", report)

    joblib.dump(encoder, model_dir / "encoder.joblib")
    joblib.dump(clf, model_dir / "classifier.joblib")
    logger.info("Model saved to %s", model_dir)


_category_encoder = None
_category_classifier = None


def _load_model(model_dir: Path) -> None:
    global _category_encoder, _category_classifier
    if _category_encoder is not None:
        return

    model_dir = Path(model_dir)
    encoder_path = model_dir / "encoder.joblib"
    clf_path = model_dir / "classifier.joblib"

    if not encoder_path.exists() or not clf_path.exists():
        raise FileNotFoundError(
            f"Category model not found at {model_dir}. "
            "Run train_category_model(csv_path, model_dir) first."
        )

    _category_encoder = joblib.load(encoder_path)
    _category_classifier = joblib.load(clf_path)


def predict_category(
    subject: str,
    body: str,
    sender: str,
    model_dir: Optional[Path] = None,
) -> dict:
    """
    Predict category for an email.

    Returns:
        {"label": str, "confidence": float}
    """
    if not _has_deps:
        raise ImportError(
            "Required: sentence-transformers, scikit-learn, pandas, joblib"
        )

    if model_dir is None:
        from .config import MODELS_DIR

        model_dir = MODELS_DIR / "category"

    _load_model(model_dir)

    text = f"{subject} [SEP] {sender} [SEP] {body[:2000]}"
    embedding = _category_encoder.encode([text])
    proba = _category_classifier.predict_proba(embedding)[0]
    pred_idx = proba.argmax()
    label = _category_classifier.classes_[pred_idx]
    confidence = float(proba[pred_idx])

    return {"label": label, "confidence": confidence}


def clear_model_cache() -> None:
    """Clear cached model (useful for testing or reloading)."""
    global _category_encoder, _category_classifier
    _category_encoder = None
    _category_classifier = None