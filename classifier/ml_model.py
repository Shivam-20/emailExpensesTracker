"""
classifier/ml_model.py — Stage 2: TF-IDF + Naive Bayes classifier.

CLI:
    python -m classifier.ml_model --train
    python -m classifier.ml_model --retrain   (merge feedback, then retrain)

Public API:
    predict(email: EmailInput) -> dict
    train(csv_path, ...)
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Lazy imports so the app starts even without scikit-learn installed ─────────
try:
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False
    logger.warning("scikit-learn / pandas / joblib not installed — ML stage disabled")


def _build_pipeline() -> "Pipeline":
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=10_000,
            sublinear_tf=True,
        )),
        ("clf", MultinomialNB(alpha=0.5)),
    ])


def _load_csv(csv_path: Path) -> "pd.DataFrame":
    """Load and validate a training/feedback CSV."""
    df = pd.read_csv(csv_path)
    required = {"subject", "body", "sender", "label"}
    if not required.issubset(df.columns):
        raise ValueError(f"{csv_path} must have columns: {required}")
    df = df.dropna(subset=["subject", "label"])
    df["text"] = (
        df["subject"].fillna("") + " "
        + df["sender"].fillna("") + " "
        + df["body"].fillna("").str[:3000]
    ).str.lower().str.strip()
    return df


def train(
    csv_path: Path,
    model_path: Path,
    vectorizer_path: Path,
    verbose: bool = True,
) -> None:
    """Train TF-IDF + Naive Bayes on csv_path and save artifacts."""
    if not _HAS_SKLEARN:
        raise ImportError("scikit-learn and pandas are required for training.")

    df = _load_csv(csv_path)
    # Keep only EXPENSE / NOT_EXPENSE rows
    df = df[df["label"].isin(["EXPENSE", "NOT_EXPENSE"])].copy()
    logger.info("Training on %d rows (%s)", len(df), csv_path.name)

    X = df["text"].tolist()
    y = df["label"].tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    if verbose:
        y_pred = pipeline.predict(X_test)
        report = classification_report(y_test, y_pred)
        logger.info("Eval on %d test rows:\n%s", len(y_test), report)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    logger.info("Model saved → %s", model_path)


def retrain(
    base_csv: Path,
    feedback_csv: Path,
    model_path: Path,
    vectorizer_path: Path,
) -> None:
    """Merge feedback into base CSV and retrain."""
    if not _HAS_SKLEARN:
        raise ImportError("scikit-learn and pandas are required for retraining.")
    if not feedback_csv.exists():
        logger.warning("No feedback file at %s — training on base data only", feedback_csv)
        train(base_csv, model_path, vectorizer_path)
        return

    base_df     = _load_csv(base_csv)
    feedback_df = _load_csv(feedback_csv)
    merged      = pd.concat([base_df, feedback_df], ignore_index=True)
    merged      = merged.drop_duplicates(subset=["subject", "body"])

    tmp_path = base_csv.parent / "_merged_training.csv"
    merged.to_csv(tmp_path, index=False)
    logger.info("Merged %d base + %d feedback rows", len(base_df), len(feedback_df))
    train(tmp_path, model_path, vectorizer_path)
    tmp_path.unlink(missing_ok=True)


# ── Module-level cached pipeline ──────────────────────────────────────────────
_pipeline: Optional["Pipeline"] = None


def _load_pipeline() -> "Pipeline":
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    from .config import MODEL_PATH
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"ML model not found at {MODEL_PATH}. "
            "Run: python -m classifier.ml_model --train"
        )
    _pipeline = joblib.load(MODEL_PATH)
    return _pipeline


def predict(email: "EmailInput") -> dict:  # type: ignore[name-defined]
    """
    Predict label and probability for a single email.

    Returns:
        {"label": "EXPENSE"|"NOT_EXPENSE", "probability": float}
    """
    if not _HAS_SKLEARN:
        raise ImportError("scikit-learn is not installed — ML stage unavailable")

    from .schemas import EmailInput  # noqa: F401 (type check)

    pipeline = _load_pipeline()
    text = f"{email.subject} {email.sender} {email.body[:3000]}".lower().strip()

    proba = pipeline.predict_proba([text])[0]
    classes: list[str] = pipeline.classes_.tolist()
    expense_idx = classes.index("EXPENSE") if "EXPENSE" in classes else 0

    label = classes[int(proba.argmax())]
    probability = float(proba[expense_idx] if label == "EXPENSE" else 1 - proba[expense_idx])
    return {"label": label, "probability": probability}


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Train/retrain the ML model")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--train",   action="store_true", help="Train on base CSV")
    group.add_argument("--retrain", action="store_true", help="Merge feedback and retrain")
    args = parser.parse_args()

    from .config import (
        FEEDBACK_CSV, MODEL_PATH, TRAINING_CSV, VECTORIZER_PATH
    )

    if args.train:
        train(TRAINING_CSV, MODEL_PATH, VECTORIZER_PATH)
    elif args.retrain:
        retrain(TRAINING_CSV, FEEDBACK_CSV, MODEL_PATH, VECTORIZER_PATH)
