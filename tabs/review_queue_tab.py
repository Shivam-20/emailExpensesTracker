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
from styles import ACCENT, BORDER, SURFACE, TEXT, TEXT_DIM, WARNING, SUCCESS, ERROR

logger = logging.getLogger(__name__)

COLUMNS = ["Date", "Sender", "Subject", "AI Label", "Confidence", "Correct Label", "Category", "Action"]
CI = {name: i for i, name in enumerate(COLUMNS)}


class ReviewQueueTab(QWidget):
    """Tab 4 — Review Queue for emails needing human classification."""

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

        # Header row
        header = QHBoxLayout()
        title = QLabel("Emails needing review")
        title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: bold;")
        header.addWidget(title)

        self._count_label = QLabel("0 items")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM};")
        header.addStretch()
        header.addWidget(self._count_label)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("ghostBtn")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Bulk action bar
        bulk_bar = QWidget()
        bulk_lay = QHBoxLayout(bulk_bar)
        bulk_lay.setContentsMargins(0, 0, 0, 0)
        bulk_lay.setSpacing(8)

        dismiss_all_btn = QPushButton("🚫 Dismiss All (Not Expense)")
        dismiss_all_btn.setObjectName("ghostBtn")
        dismiss_all_btn.setToolTip("Mark all queued items as NOT_EXPENSE and remove from queue")
        dismiss_all_btn.clicked.connect(self._dismiss_all)
        bulk_lay.addWidget(dismiss_all_btn)

        accept_all_btn = QPushButton("✅ Accept All as Expense")
        accept_all_btn.setObjectName("ghostBtn")
        accept_all_btn.setToolTip("Mark all queued items as EXPENSE")
        accept_all_btn.clicked.connect(self._accept_all)
        bulk_lay.addWidget(accept_all_btn)

        bulk_lay.addStretch()
        layout.addWidget(bulk_bar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(CI["Date"],          QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Sender"],        QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["Subject"],       QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["AI Label"],      QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Confidence"],    QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Correct Label"], QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Category"],      QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Action"],        QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Empty state
        self._empty_label = QLabel("No emails pending review.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {TEXT_DIM}; padding: 40px;")
        layout.addWidget(self._empty_label)

    # ── Data loading ───────────────────────────────────────────────────────

    def refresh(self) -> None:
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

            # AI Label — show the actual classifier decision
            source = row.get("classification_source", "unknown")
            label_map = {
                "rules":        "EXPENSE (rules)",
                "ml":           "EXPENSE (ML)",
                "distilbert":   "REVIEW (DistilBERT)",
                "phi4-mini":    "REVIEW (phi4-mini)",
                "human_review": "REVIEWED",
            }
            ai_label = label_map.get(source, source)
            ai_item = _item(ai_label, center=True)
            self._table.setItem(i, CI["AI Label"], ai_item)

            # Confidence band
            conf = row.get("confidence", "")
            conf_item = _item(conf or "—", center=True)
            conf_colors = {"HIGH": SUCCESS, "MEDIUM": WARNING, "LOW": ERROR}
            if conf in conf_colors:
                from PyQt6.QtGui import QColor
                conf_item.setForeground(QColor(conf_colors[conf]))
            self._table.setItem(i, CI["Confidence"], conf_item)

            # Correct Label dropdown
            label_combo = QComboBox()
            label_combo.addItems(["EXPENSE", "NOT_EXPENSE"])
            self._table.setCellWidget(i, CI["Correct Label"], label_combo)

            # Category dropdown (for EXPENSE corrections)
            cat_combo = QComboBox()
            cat_combo.addItems(ALL_CATEGORIES)
            current_cat = row.get("category_edited") or row.get("category", "Other")
            if current_cat in ALL_CATEGORIES:
                cat_combo.setCurrentText(current_cat)
            # Show/hide based on label selection
            label_combo.currentTextChanged.connect(
                lambda text, cc=cat_combo: cc.setEnabled(text == "EXPENSE")
            )
            self._table.setCellWidget(i, CI["Category"], cat_combo)

            # Save button
            msg_id = row.get("id", "")
            save_btn = QPushButton("Save")
            save_btn.setObjectName("ghostBtn")
            save_btn.clicked.connect(
                lambda _, r=i, mid=msg_id: self._on_save(r, mid)
            )
            self._table.setCellWidget(i, CI["Action"], save_btn)

    def get_review_count(self) -> int:
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
        label_combo = self._table.cellWidget(table_row, CI["Correct Label"])
        cat_combo   = self._table.cellWidget(table_row, CI["Category"])
        if not label_combo:
            return
        correct_label = label_combo.currentText()
        correct_cat   = cat_combo.currentText() if cat_combo else None

        row = self._rows[table_row] if table_row < len(self._rows) else None
        if not row:
            return

        self._write_feedback(row, correct_label)

        if self._db:
            try:
                updates = {
                    "needs_review": 0,
                    "status": "active",
                    "classification_source": "human_review",
                }
                if correct_label == "EXPENSE" and correct_cat:
                    updates["category_edited"] = correct_cat
                elif correct_label == "NOT_EXPENSE":
                    updates["status"] = "excluded"

                set_clause = ", ".join(f"{k} = ?" for k in updates)
                self._db.conn.execute(
                    f"UPDATE expenses SET {set_clause} WHERE id = ?",
                    list(updates.values()) + [msg_id],
                )
                self._db.conn.commit()
            except Exception as exc:
                logger.error("Failed to update review status: %s", exc)
                QMessageBox.warning(self, "Error", f"Could not save: {exc}")
                return

        self.correction_saved.emit(msg_id, correct_label)
        if table_row < len(self._rows):
            self._rows.pop(table_row)
        self._populate_table()

    # ── Bulk actions ───────────────────────────────────────────────────────

    def _dismiss_all(self) -> None:
        if not self._rows:
            return
        reply = QMessageBox.question(
            self, "Dismiss All",
            f"Mark all {len(self._rows)} items as NOT_EXPENSE?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for row in list(self._rows):
            self._write_feedback(row, "NOT_EXPENSE")
            if self._db:
                try:
                    self._db.conn.execute(
                        "UPDATE expenses SET needs_review = 0, status = 'excluded', "
                        "classification_source = 'human_review' WHERE id = ?",
                        (row.get("id"),),
                    )
                except Exception as exc:
                    logger.error("Dismiss all failed for %s: %s", row.get("id"), exc)
        if self._db:
            self._db.conn.commit()
        self._rows.clear()
        self._populate_table()

    def _accept_all(self) -> None:
        if not self._rows:
            return
        reply = QMessageBox.question(
            self, "Accept All",
            f"Mark all {len(self._rows)} items as EXPENSE?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for row in list(self._rows):
            self._write_feedback(row, "EXPENSE")
            if self._db:
                try:
                    self._db.conn.execute(
                        "UPDATE expenses SET needs_review = 0, status = 'active', "
                        "classification_source = 'human_review' WHERE id = ?",
                        (row.get("id"),),
                    )
                except Exception as exc:
                    logger.error("Accept all failed for %s: %s", row.get("id"), exc)
        if self._db:
            self._db.conn.commit()
        self._rows.clear()
        self._populate_table()

    # ── Feedback CSV ───────────────────────────────────────────────────────

    def _write_feedback(self, row: dict, correct_label: str) -> None:
        if not self._data_dir:
            return
        feedback_path = self._data_dir / "data" / "feedback.csv"
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
