"""
classifier/cache.py — SQLite cache for LLM classification results.

Cache key: SHA-256 of (subject + body + sender + attachments).
Also keyed on model_name + prompt_version + model_hash to invalidate on
model/prompt changes and after retraining.
REVIEW outcomes are never cached.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import LLM_MODEL_NAME, MODELS_DIR, PROMPT_VERSION
from .utils import sha256_hash

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (
    hash             TEXT NOT NULL,
    model_name       TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    model_hash       TEXT NOT NULL DEFAULT '',
    label            TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    confidence_band  TEXT NOT NULL,
    reason           TEXT,
    created_at       TEXT NOT NULL,
    PRIMARY KEY (hash, model_name, prompt_version, model_hash)
);
"""

# Module-level cached model hash (computed once per session)
_model_hash_cache: Optional[str] = None


def _compute_model_hash() -> str:
    """Return a short hash based on model file modification times.

    Covers both joblib (NB) and DistilBERT model files so the cache
    auto-invalidates after any retraining.
    """
    global _model_hash_cache
    if _model_hash_cache is not None:
        return _model_hash_cache

    paths = sorted(
        list(MODELS_DIR.glob("**/*.bin"))
        + list(MODELS_DIR.glob("**/*.joblib"))
        + list(MODELS_DIR.glob("**/*.safetensors"))
    )
    digest = hashlib.md5(
        b"".join(
            str(p.stat().st_mtime_ns).encode()
            for p in paths
            if p.exists()
        )
    ).hexdigest()[:8]
    _model_hash_cache = digest
    return digest


def reset_model_hash() -> None:
    """Clear the cached model hash so it is recomputed on next access.

    Call this after retraining a model within the same process.
    """
    global _model_hash_cache
    _model_hash_cache = None


class PredictionCache:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._model_hash = _compute_model_hash()
        logger.debug("Cache DB opened at %s (model_hash=%s)", db_path, self._model_hash)

    def get(
        self,
        subject: str,
        body: str,
        sender: str,
        attachments: list[str],
    ) -> Optional[dict]:
        """Return a cached result dict, or None on cache miss."""
        key = sha256_hash(subject, body, sender, attachments)
        row = self._conn.execute(
            "SELECT * FROM llm_cache "
            "WHERE hash=? AND model_name=? AND prompt_version=? AND model_hash=?",
            (key, LLM_MODEL_NAME, PROMPT_VERSION, self._model_hash),
        ).fetchone()
        if row:
            logger.debug("Cache hit for hash=%s", key[:12])
            return dict(row)
        return None

    def set(
        self,
        subject: str,
        body: str,
        sender: str,
        attachments: list[str],
        result: dict,
    ) -> None:
        """Store a result. REVIEW outcomes are silently skipped."""
        if result.get("label") == "REVIEW":
            return
        key = sha256_hash(subject, body, sender, attachments)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO llm_cache
                (hash, model_name, prompt_version, model_hash, label,
                 confidence_score, confidence_band, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                LLM_MODEL_NAME,
                PROMPT_VERSION,
                self._model_hash,
                result["label"],
                result.get("confidence_score", 0.0),
                result.get("confidence_band", "low"),
                result.get("reason", ""),
                datetime.utcnow().isoformat(),
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
