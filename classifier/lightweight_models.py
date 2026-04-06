"""
classifier/lightweight_models.py — Lightweight transformer models for email classification.

Supports: MiniLM-L6-V2, TinyBERT, ALBERT, MobileBERT, DistilBERT

Public API:
    MODEL_CONFIGS: dict of model configurations
    train_model(model_type, csv_path, model_dir)
    predict(model_type, subject, sender, body) -> dict
    load_model(model_type, model_dir) -> (embedding_model, classifier)
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from classifier.config import (
    LIGHTWEIGHT_MODEL_DIR,
    check_model_exists,
    check_for_model_updates,
    download_model_from_release,
)

_MODEL_CACHE: dict[str, tuple[Any, Any]] = {}
_PIPELINE_CACHE: dict[str, Any] = {}

logger = logging.getLogger(__name__)

try:
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False
    logger.warning("scikit-learn not installed — lightweight models unavailable")

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False
    logger.warning("sentence-transformers not installed — MiniLM unavailable")

try:
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        pipeline,
    )
    _HAS_TRANSFORMERS = True
    _HAS_DATASETS = True
except ImportError:
    _HAS_TRANSFORMERS = False
    _HAS_DATASETS = False
    logger.warning("transformers not installed — BERT models unavailable")

# Check for model updates on import
try:
    update_available, new_version = check_for_model_updates()
    if update_available:
        logger.info(f"Model update available: {new_version}")
except Exception:
    pass

MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "minilm": {
        "name": "sentence-transformers/all-MiniLM-L6-V2",
        "params": "22M",
        "description": "MiniLM-L6-V2 - fastest, smallest footprint",
        "type": "embedding",
    },
    "tinybert": {
        "name": "huawei-noah/TinyBERT_General_4L_312D",
        "params": "14M",
        "description": "TinyBERT 4L - smallest BERT variant",
        "type": "classifier",
    },
    "albert": {
        "name": "albert-base-v2",
        "params": "12M",
        "description": "ALBERT base - parameter efficient",
        "type": "classifier",
    },
    "mobilebert": {
        "name": "google/mobilebert-uncased",
        "params": "25M",
        "description": "MobileBERT - optimized for mobile CPUs",
        "type": "classifier",
    },
    "distilbert": {
        "name": "distilbert-base-uncased",
        "params": "67M",
        "description": "DistilBERT - faster BERT with good accuracy",
        "type": "classifier",
    },
}


def _load_csv(csv_path: Path) -> "pd.DataFrame":
    """Load and validate training CSV."""
    df = pd.read_csv(csv_path)
    required = {"subject", "body", "sender", "label"}
    if not required.issubset(df.columns):
        raise ValueError(f"{csv_path} must have columns: {required}")
    df = df.dropna(subset=["subject", "label"])
    df = df[df["label"].isin(["EXPENSE", "NOT_EXPENSE"])].copy()
    df["text"] = (
        df["subject"].fillna("") + " " + df["sender"].fillna("") + " " + df["body"].fillna("")
    ).str.lower().str.strip()
    return df


def _get_embeddings(texts: list[str], model_name: str) -> "np.ndarray":
    """Get embeddings using sentence-transformers."""
    if not _HAS_SENTENCE_TRANSFORMERS:
        raise ImportError("sentence-transformers required for embedding models")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings


def train_model(model_type: str, csv_path: Path, model_dir: Path) -> None:
    """Train a lightweight model on email classification data."""
    if model_type not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(MODEL_CONFIGS.keys())}")

    if not _HAS_SKLEARN:
        raise ImportError("scikit-learn required for training")

    config = MODEL_CONFIGS[model_type]
    model_dir = Path(model_dir) / model_type
    model_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading training data from %s", csv_path)
    df = _load_csv(csv_path)
    logger.info("Training on %d samples", len(df))

    X = df["text"].tolist()
    y = df["label"].tolist()

    if config["type"] == "embedding":
        _train_embedding_model(model_type, config["name"], X, y, model_dir)
    else:
        _train_classifier_model(model_type, config["name"], X, y, df, model_dir)


def _train_embedding_model(
    model_type: str, model_name: str, X: list[str], y: list[str], model_dir: Path
) -> None:
    """Train embedding + LogisticRegression classifier."""
    logger.info("Generating embeddings with %s", model_name)
    X_embeddings = _get_embeddings(X, model_name)

    X_train, X_test, y_train, y_test = train_test_split(
        X_embeddings, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info("Training LogisticRegression classifier")
    clf = LogisticRegression(max_iter=1000, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred)
    logger.info("Evaluation:\n%s", report)

    model_path = model_dir / "classifier.joblib"
    joblib.dump(clf, model_path)

    if not model_path.exists():
        raise RuntimeError(f"Failed to save classifier to {model_path}")

    logger.info("Classifier saved to %s", model_path)


def _train_classifier_model(
    model_type: str, model_name: str, X: list[str], y: list[str], df: "pd.DataFrame", model_dir: Path
) -> None:
    """Train transformer classifier with fine-tuning."""
    if not _HAS_TRANSFORMERS:
        raise ImportError("transformers required for classifier models")

    if not _HAS_DATASETS:
        raise ImportError("datasets required for classifier training")

    logger.info("Loading tokenizer and model: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=2, ignore_mismatched_sizes=True
    )

    label2id = {"EXPENSE": 0, "NOT_EXPENSE": 1}
    id2label = {0: "EXPENSE", 1: "NOT_EXPENSE"}

    def tokenize_function(texts: list[str]) -> Any:
        return tokenizer(texts, padding=True, truncation=True, max_length=384)

    encodings = tokenize_function(X)
    labels = [label2id[label] for label in y]

    dataset = Dataset.from_dict({"input_ids": encodings["input_ids"], "attention_mask": encodings["attention_mask"], "labels": labels})

    train_idx, test_idx = train_test_split(range(len(dataset)), test_size=0.2, random_state=42, stratify=labels)
    train_dataset = dataset.select(train_idx)
    eval_dataset = dataset.select(test_idx)

    training_args = TrainingArguments(
        output_dir=str(model_dir / "checkpoints"),
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
    )

    logger.info("Training %s classifier", model_type)
    trainer.train()

    eval_results = trainer.evaluate()
    logger.info("Evaluation results: %s", eval_results)

    model_path = model_dir / "pytorch_model.bin"
    tokenizer_path = model_dir / "tokenizer"

    model.save_pretrained(model_path.parent)
    tokenizer.save_pretrained(tokenizer_path)

    if not model_path.parent.exists():
        raise RuntimeError(f"Failed to save model to {model_path.parent}")

    logger.info("Model saved to %s", model_dir)

    global _MODEL_CACHE
    _MODEL_CACHE.clear()


def load_model(model_type: str, model_dir: Path) -> tuple[Any, Any]:
    """Load a trained model for inference. Returns (embedding_model, classifier)."""
    if model_type not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model type: {model_type}")

    cache_key = f"{model_type}:{model_dir}"
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    model_dir = Path(model_dir) / model_type

    if not model_dir.exists():
        logger.info(f"Model {model_type} not found locally, attempting download...")
        success = download_model_from_release(model_type, model_dir.parent)
        if not success:
            raise FileNotFoundError(
                f"Model {model_type} not found locally and could not download"
            )

    config = MODEL_CONFIGS[model_type]

    if config["type"] == "embedding":
        embedding_model = SentenceTransformer(config["name"])
        classifier = joblib.load(model_dir / "classifier.joblib")
        result = (embedding_model, classifier)
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        result = (model, tokenizer)

    _MODEL_CACHE[cache_key] = result
    return result


def predict(model_type: str, subject: str, sender: str, body: str) -> dict[str, Any]:
    """Predict label and confidence for an email."""
    if model_type not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model type: {model_type}")

    from .config import LIGHTWEIGHT_MODEL_DIR

    model_or_embedding, tokenizer_or_classifier = load_model(model_type, LIGHTWEIGHT_MODEL_DIR)

    text = f"{subject} {sender} {body}".lower().strip()
    config = MODEL_CONFIGS[model_type]

    if config["type"] == "embedding":
        embedding = model_or_embedding.encode([text])
        proba = tokenizer_or_classifier.predict_proba(embedding)[0]
        pred_idx = int(proba.argmax())
        label = tokenizer_or_classifier.classes_[pred_idx]
        confidence = float(proba[pred_idx])
        probas = {"EXPENSE": float(proba[0]), "NOT_EXPENSE": float(proba[1])}
    else:
        classifier_pipe = pipeline(
            "text-classification",
            model=model_or_embedding,
            tokenizer=tokenizer_or_classifier,
        )
        result = classifier_pipe(text)[0]
        label = result["label"]
        confidence = result["score"]
        probas = {
            "EXPENSE": confidence if label == "EXPENSE" else 1 - confidence,
            "NOT_EXPENSE": 1 - confidence if label == "EXPENSE" else confidence,
        }

    return {
        "label": str(label),
        "confidence": confidence,
        "probas": probas,
    }