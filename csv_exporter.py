"""
csv_exporter.py — Export visible expense rows to a CSV file.
"""

import csv
import logging
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from expense_parser import Expense

logger = logging.getLogger(__name__)

CSV_HEADERS = ["Date", "Sender", "Sender Email", "Subject", "Amount", "Currency",
               "Category", "Snippet"]


def export_to_csv(
    parent: QWidget,
    expenses: list[Expense],
    default_year: int,
    default_month: int,
) -> None:
    """
    Open a Save File dialog and write *expenses* to a CSV.
    Shows a success/failure QMessageBox when done.
    """
    if not expenses:
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
        return   # user cancelled

    try:
        with open(file_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for exp in expenses:
                writer.writerow({
                    "Date":         exp.date,
                    "Sender":       exp.sender,
                    "Sender Email": exp.sender_email,
                    "Subject":      exp.subject,
                    "Amount":       f"{exp.amount:.2f}",
                    "Currency":     exp.currency,
                    "Category":     exp.category,
                    "Snippet":      exp.snippet,
                })
        QMessageBox.information(
            parent,
            "Export Successful",
            f"✅ {len(expenses)} expense(s) saved to:\n{file_path}",
        )
        logger.info("Exported %d expenses to %s", len(expenses), file_path)
    except OSError as exc:
        QMessageBox.critical(parent, "Export Failed", f"Could not write file:\n{exc}")
        logger.error("CSV export failed: %s", exc)
