"""
core/csv_exporter.py — Export visible expense rows to CSV.
"""

import csv
import json
import logging
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "Date", "Sender", "Sender Email", "Subject",
    "Amount", "Currency", "Payment Method",
    "Category", "Tags", "Confidence", "Status", "Notes",
]


def export_to_csv(
    parent: QWidget,
    rows: list[dict],
    default_year: int,
    default_month: int,
) -> None:
    """Open Save dialog and write *rows* to CSV."""
    if not rows:
        QMessageBox.information(parent, "Nothing to Export",
                                "There are no expenses to export.")
        return

    default_name = f"expenses_{default_year}_{default_month:02d}.csv"
    default_path = str(Path.home() / default_name)

    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Export Expenses to CSV",
        default_path,
        "CSV Files (*.csv);;All Files (*)",
    )
    if not file_path:
        return

    try:
        with open(file_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for row in rows:
                # Effective amount: user-edited takes precedence
                amount = row.get("amount_edited") or row.get("amount") or 0
                # Tags: JSON array → semicolon string
                try:
                    tags_list = json.loads(row.get("tags") or "[]")
                except (ValueError, TypeError):
                    tags_list = []
                tags_str = "; ".join(tags_list)

                writer.writerow({
                    "Date":           row.get("email_date", ""),
                    "Sender":         row.get("sender", ""),
                    "Sender Email":   row.get("sender_email", ""),
                    "Subject":        row.get("subject", ""),
                    "Amount":         f"{amount:.2f}",
                    "Currency":       row.get("currency", "INR"),
                    "Payment Method": row.get("payment_method", "Unknown"),
                    "Category":       row.get("category_edited") or row.get("category", "Other"),
                    "Tags":           tags_str,
                    "Confidence":     row.get("confidence", ""),
                    "Status":         row.get("status", "active"),
                    "Notes":          row.get("notes", ""),
                })

        QMessageBox.information(
            parent,
            "Export Successful",
            f"✅ {len(rows)} row(s) saved to:\n{file_path}",
        )
        logger.info("Exported %d rows to %s", len(rows), file_path)

    except OSError as exc:
        QMessageBox.critical(parent, "Export Failed", f"Could not write file:\n{exc}")
        logger.error("CSV export failed: %s", exc)
