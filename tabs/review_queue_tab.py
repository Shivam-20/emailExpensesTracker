"""
tabs/review_queue_tab.py — Review Queue: shows emails classified as REVIEW
with inline correction UI for feeding back into the training pipeline.
"""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from config.category_map import ALL_CATEGORIES
from styles import ACCENT, BORDER, SURFACE, TEXT, TEXT_DIM, WARNING

logger = logging.getLogger(__name__)

COLUMNS = ["Date", "Sender", "Subject", "Suggested", "Correct Label", "Action"]
CI = {name: i for i, name in enumerate(COLUMNS)}


class ReviewQueueTab(QWidget):
    """Tab 5 — Review Queue for emails needing human classification."""

    # Emitted when a correction is saved (msg_id, new_label)
    correction_saved = pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = None
        self._data_dir: Optional[Path] = None
        self._rows: list[dict] = []
        self._setup_ui()

    def set_db(self, db, data_dir: Path) -> None:
        self._db = db
        self._data_dir = data_dir

    # ── UI ─────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Emails needing review")
        title.setObjectName("statusLabel")
        title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: bold;")
        header.addWidget(title)

        self._count_label = QLabel("0 items")
        self._count_label.setObjectName("statusLabel")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM};")
        header.addStretch()
        header.addWidget(self._count_label)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("ghostBtn")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(CI["Date"],    QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Sender"],  QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["Subject"], QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["Suggested"], QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Correct Label"], QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Action"],  QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Empty state
        self._empty_label = QLabel("No emails pending review.")
        self._empty_label.setObjectName("statusLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {TEXT_DIM}; padding: 40px;")
        layout.addWidget(self._empty_label)

    # ── Data loading ───────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Load all rows with needs_review=1 or status='review' from DB."""
        if not self._db:
            return

        try:
            rows = self._db.conn.execute(
                "SELECT * FROM expenses WHERE needs_review = 1 OR status = 'review' "
                "ORDER BY email_date DESC"
            ).fetchall()
            self._rows = [dict(r) for r in rows]
        except Exception as exc:
            logger.error("Failed to load review queue: %s", exc)
            self._rows = []

        self._populate_table()

    def _populate_table(self) -> None:
        rows = self._rows
        count = len(rows)
        self._count_label.setText(f"{count} item{'s' if count != 1 else ''}")

        self._table.setVisible(count > 0)
        self._empty_label.setVisible(count == 0)

        self._table.setRowCount(count)
        for i, row in enumerate(rows):
            # Date
            date_str = (row.get("email_date") or "")[:10]
            self._table.setItem(i, CI["Date"], _item(date_str, center=True))

            # Sender
            sender = row.get("sender") or row.get("sender_email") or ""
            self._table.setItem(i, CI["Sender"], _item(sender))

            # Subject
            self._table.setItem(i, CI["Subject"], _item(row.get("subject", "")))

            # Suggested label (from classification)
            suggested = row.get("classification_source", "unknown")
            self._table.setItem(i, CI["Suggested"], _item(suggested, center=True))

            # Correct Label dropdown
            combo = QComboBox()
            combo.addItems(["EXPENSE", "NOT_EXPENSE"])
            self._table.setCellWidget(i, CI["Correct Label"], combo)

            # Save button
            save_btn = QPushButton("Save")
            save_btn.setObjectName("ghostBtn")
            msg_id = row.get("id", "")
            save_btn.clicked.connect(
                lambda _, r=i, mid=msg_id: self._on_save(r, mid)
            )
            self._table.setCellWidget(i, CI["Action"], save_btn)

    def get_review_count(self) -> int:
        """Return the number of items in the review queue."""
        if not self._db:
            return 0
        try:
            row = self._db.conn.execute(
                "SELECT COUNT(*) FROM expenses WHERE needs_review = 1 OR status = 'review'"
            ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    # ── Save correction ────────────────────────────────────────────────────

    def _on_save(self, table_row: int, msg_id: str) -> None:
        combo = self._table.cellWidget(table_row, CI["Correct Label"])
        if not combo:
            return
        correct_label = combo.currentText()

        # Get the original row data for feedback CSV
        row = self._rows[table_row] if table_row < len(self._rows) else None
        if not row:
            return

        # Write to feedback.csv
        self._write_feedback(row, correct_label)

        # Update DB: mark as reviewed, set new label
        if self._db:
            try:
                self._db.conn.execute(
                    "UPDATE expenses SET needs_review = 0, status = 'active', "
                    "classification_source = 'human_review' WHERE id = ?",
                    (msg_id,),
                )
                self._db.conn.commit()
            except Exception as exc:
                logger.error("Failed to update review status: %s", exc)
                QMessageBox.warning(self, "Error", f"Could not save: {exc}")
                return

        self.correction_saved.emit(msg_id, correct_label)

        # Remove from local list and refresh table
        if table_row < len(self._rows):
            self._rows.pop(table_row)
        self._populate_table()

    def _write_feedback(self, row: dict, correct_label: str) -> None:
        """Append a correction row to data/feedback.csv."""
        if not self._data_dir:
            return

        feedback_path = self._data_dir / "data" / "feedback.csv"
        # Use project-level data/ if data_dir doesn't have it
        if not feedback_path.parent.exists():
            from classifier.config import FEEDBACK_CSV
            feedback_path = FEEDBACK_CSV

        is_new = not feedback_path.exists()
        feedback_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with feedback_path.open("a", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                if is_new:
                    writer.writerow(["subject", "body", "sender", "label"])
                writer.writerow([
                    row.get("subject", ""),
                    row.get("snippet", ""),
                    row.get("sender_email", row.get("sender", "")),
                    correct_label,
                ])
        except OSError as exc:
            logger.error("Failed to write feedback: %s", exc)


# ── Helpers ────────────────────────────────────────────────────────────────

def _item(text: str, center: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if center:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it
