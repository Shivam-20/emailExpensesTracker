"""
classifier/cache.py — SQLite cache for LLM classification results.

Cache key: SHA-256 of (subject + body + sender + attachments).
Also keyed on model_name + prompt_version to invalidate on model/prompt changes.
REVIEW outcomes are never cached.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import LLM_MODEL_NAME, PROMPT_VERSION
from .utils import sha256_hash

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (
    hash             TEXT NOT NULL,
    model_name       TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    label            TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    confidence_band  TEXT NOT NULL,
    reason           TEXT,
    created_at       TEXT NOT NULL,
    PRIMARY KEY (hash, model_name, prompt_version)
);
"""


class PredictionCache:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.debug("Cache DB opened at %s", db_path)

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
            "SELECT * FROM llm_cache WHERE hash=? AND model_name=? AND prompt_version=?",
            (key, LLM_MODEL_NAME, PROMPT_VERSION),
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
                (hash, model_name, prompt_version, label, confidence_score,
                 confidence_band, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                LLM_MODEL_NAME,
                PROMPT_VERSION,
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
