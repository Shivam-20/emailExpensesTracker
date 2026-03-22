"""
classifier/distilbert_model.py — Stage 3 Option A: DistilBERT fine-tuned classifier.

Uses DistilBertForSequenceClassification fine-tuned on training_emails.csv.
Falls back to REVIEW when no fine-tuned model is present.

CLI:
    python -m classifier.distilbert_model --train
    python -m classifier.distilbert_model --retrain   (merge feedback, retrain)
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

from .schemas import EmailInput

logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False
    logger.warning("transformers / torch not installed — DistilBERT stage disabled")

# ── Module-level cache ────────────────────────────────────────────────────────
_model    = None
_tokenizer = None
_label_map: dict[int, str] = {}


def _load_model():
    """Load fine-tuned model from DISTILBERT_MODEL_DIR, or raise FileNotFoundError."""
    global _model, _tokenizer, _label_map
    if _model is not None:
        return

    from .config import DISTILBERT_MODEL_DIR

    if not DISTILBERT_MODEL_DIR.exists():
        raise FileNotFoundError(
            f"Fine-tuned DistilBERT model not found at {DISTILBERT_MODEL_DIR}. "
            "Run: bash scripts/train_classifier.sh --distilbert"
        )

    _tokenizer = AutoTokenizer.from_pretrained(str(DISTILBERT_MODEL_DIR))
    _model     = AutoModelForSequenceClassification.from_pretrained(
        str(DISTILBERT_MODEL_DIR)
    )
    _model.eval()

    # Rebuild label map from model config
    id2label: dict = _model.config.id2label or {}
    _label_map = {int(k): v for k, v in id2label.items()}
    logger.info("DistilBERT model loaded from %s", DISTILBERT_MODEL_DIR)


def classify(email: EmailInput) -> dict:
    """
    Classify a single email using DistilBERT.

    Returns a dict compatible with router.py Stage 3 handling:
        label, confidence_score, confidence_band, reason
    """
    if not _HAS_TRANSFORMERS:
        return {
            "label": "REVIEW", "confidence_score": 0.0,
            "confidence_band": "low",
            "reason": "transformers/torch not installed",
        }

    try:
        _load_model()
    except FileNotFoundError as exc:
        logger.warning("%s", exc)
        return {
            "label": "REVIEW", "confidence_score": 0.0,
            "confidence_band": "low",
            "reason": "DistilBERT model not trained yet",
        }

    from .config import DISTILBERT_HIGH_THRESHOLD, DISTILBERT_LOW_THRESHOLD, DISTILBERT_MAX_LENGTH

    text = f"{email.subject} {email.body[:1000]}".strip() or " "

    inputs = _tokenizer(
        text,
        truncation=True,
        max_length=DISTILBERT_MAX_LENGTH,
        return_tensors="pt",
    )

    with torch.no_grad():
        logits = _model(**inputs).logits
        probs  = torch.softmax(logits, dim=-1)[0]

    pred_idx   = int(probs.argmax())
    pred_label = _label_map.get(pred_idx, "REVIEW")
    confidence = float(probs[pred_idx])

    if confidence >= DISTILBERT_HIGH_THRESHOLD:
        band = "high"
    elif confidence >= DISTILBERT_LOW_THRESHOLD:
        band = "medium"
    else:
        band = "low"

    return {
        "label":            pred_label,
        "confidence_score": confidence,
        "confidence_band":  band,
        "reason":           f"DistilBERT confidence {confidence:.2f}",
    }


# ── Training helpers ──────────────────────────────────────────────────────────

def _load_training_df(csv_path: Path):
    import pandas as pd
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["subject", "label"])
    df = df[df["label"].isin(["EXPENSE", "NOT_EXPENSE"])].copy()
    df["text"] = (
        df["subject"].fillna("") + " " + df["body"].fillna("").str[:1000]
    ).str.strip()
    return df


class _EmailDataset:
    def __init__(self, texts, labels, tokenizer, max_length: int) -> None:
        self._enc = tokenizer(
            texts, truncation=True, padding=True,
            max_length=max_length, return_tensors="pt",
        )
        self._labels = torch.tensor(labels)

    def __len__(self) -> int:
        return len(self._labels)

    def __getitem__(self, idx: int) -> dict:
        return {
            "input_ids":      self._enc["input_ids"][idx],
            "attention_mask": self._enc["attention_mask"][idx],
            "labels":         self._labels[idx],
        }


MIN_TRAINING_ROWS = 300


def train(csv_path: Path, output_dir: Path, force: bool = False) -> None:
    """Fine-tune DistilBERT on csv_path and save to output_dir."""
    if not _HAS_TRANSFORMERS:
        raise ImportError("transformers and torch are required for DistilBERT training.")

    import pandas as pd
    from .config import (
        DISTILBERT_BASE_MODEL, DISTILBERT_BATCH_SIZE,
        DISTILBERT_EPOCHS, DISTILBERT_MAX_LENGTH,
    )

    df = _load_training_df(csv_path)

    if len(df) < MIN_TRAINING_ROWS and not force:
        logger.warning(
            "training data has only %d rows (minimum recommended: %d). "
            "DistilBERT may produce unreliable results.",
            len(df), MIN_TRAINING_ROWS,
        )
        # In CLI mode, prompt for confirmation
        import sys
        if sys.stdin.isatty():
            answer = input(
                f"Warning: only {len(df)} rows (need {MIN_TRAINING_ROWS}+). "
                "Continue anyway? [y/N] "
            )
            if answer.strip().lower() != "y":
                logger.info("Training aborted by user.")
                return
    labels_list = sorted(df["label"].unique().tolist())
    label2id    = {l: i for i, l in enumerate(labels_list)}
    id2label    = {i: l for l, i in label2id.items()}

    logger.info("Fine-tuning DistilBERT on %d rows, labels=%s", len(df), labels_list)

    tokenizer = AutoTokenizer.from_pretrained(DISTILBERT_BASE_MODEL)
    model     = AutoModelForSequenceClassification.from_pretrained(
        DISTILBERT_BASE_MODEL,
        num_labels=len(labels_list),
        id2label=id2label,
        label2id=label2id,
    )

    y = [label2id[l] for l in df["label"].tolist()]
    dataset = _EmailDataset(df["text"].tolist(), y, tokenizer, DISTILBERT_MAX_LENGTH)

    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=DISTILBERT_EPOCHS,
        per_device_train_batch_size=DISTILBERT_BATCH_SIZE,
        save_strategy="no",
        logging_steps=10,
        report_to="none",
    )

    trainer = Trainer(model=model, args=args, train_dataset=dataset)
    trainer.train()

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    logger.info("DistilBERT fine-tuned model saved → %s", output_dir)

    # Reset cached model so next classify() call reloads fresh
    global _model, _tokenizer, _label_map
    _model = _tokenizer = None
    _label_map = {}

    # Invalidate prediction cache so stale results aren't served
    from .cache import reset_model_hash
    reset_model_hash()


def retrain(base_csv: Path, feedback_csv: Path, output_dir: Path) -> None:
    """Merge feedback into base CSV then retrain."""
    if not _HAS_TRANSFORMERS:
        raise ImportError("transformers and torch are required for DistilBERT training.")

    import pandas as pd

    if not feedback_csv.exists():
        logger.warning("No feedback file — training on base data only")
        train(base_csv, output_dir)
        return

    base_df     = pd.read_csv(base_csv)
    feedback_df = pd.read_csv(feedback_csv)
    merged      = pd.concat([base_df, feedback_df], ignore_index=True)
    merged      = merged.drop_duplicates(subset=["subject", "body"])

    tmp = base_csv.parent / "_distilbert_merged.csv"
    merged.to_csv(tmp, index=False)
    train(tmp, output_dir)
    tmp.unlink(missing_ok=True)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Fine-tune / retrain DistilBERT")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--train",   action="store_true")
    group.add_argument("--retrain", action="store_true")
    args = parser.parse_args()

    from .config import DISTILBERT_MODEL_DIR, FEEDBACK_CSV, TRAINING_CSV

    if args.train:
        train(TRAINING_CSV, DISTILBERT_MODEL_DIR)
    elif args.retrain:
        retrain(TRAINING_CSV, FEEDBACK_CSV, DISTILBERT_MODEL_DIR)
