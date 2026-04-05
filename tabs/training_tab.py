"""
tabs/training_tab.py — Training Tab: manage training data, view stats, retrain model.

Features:
- Statistics card (row count, label distribution)
- Preview table (first 50 rows, searchable)
- Add Sample modal dialog
- Retrain Model button with progress tracking
- Model performance metrics
- Download dropdown (training data versions + export DB)
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QProgressBar,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.training_data_exporter import (
    add_training_sample,
    create_backup,
    export_database,
    export_training_data,
    get_training_data_stats,
    import_training_data,
    list_backups,
    load_training_data,
    restore_backup,
)
from workers.training_worker import TrainingDataLoadWorker, TrainingWorker

from styles import (
    ACCENT, BG, BORDER, SUCCESS, SUCCESS_BG, SURFACE, SURFACE2,
    TEXT, TEXT_DIM, WARNING, WARNING_BG,
)

logger = logging.getLogger(__name__)

COLUMNS = ["#", "Subject", "Sender", "Label"]
CI = {name: i for i, name in enumerate(COLUMNS)}


class TrainingTab(QWidget):
    """Tab 6 — Training data management and model retraining."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data_dir: Optional[Path] = None
        self._db_path: Optional[Path] = None
        self._worker: Optional[TrainingWorker] = None
        self._load_worker: Optional[TrainingDataLoadWorker] = None
        self._all_rows: list[dict] = []
        self._visible_rows: list[dict] = []
        self._setup_ui()
        self._refresh_stats()
        self._load_data_async()

    def set_data_dir(self, data_dir: Path, db_path: Path) -> None:
        """Set the data directory and database path."""
        self._data_dir = data_dir
        self._db_path = db_path
        self._refresh_stats()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        # ── Header row ───────────────────────────────────────────────────
        header_row = QHBoxLayout()
        
        title = QLabel("Training Data")
        title.setObjectName("sectionLabel")
        title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: bold;")
        header_row.addWidget(title)
        
        header_row.addStretch()
        
        # Download dropdown
        self._download_btn = QPushButton("📥 Download")
        self._download_btn.setObjectName("ghostBtn")
        self._download_btn.clicked.connect(self._on_download_clicked)
        header_row.addWidget(self._download_btn)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("ghostBtn")
        refresh_btn.clicked.connect(self._refresh_all)
        header_row.addWidget(refresh_btn)
        
        layout.addLayout(header_row)

        # ── Statistics cards ──────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        
        self._total_card = _StatCard("Total Rows", "—", "#89b4fa")
        self._expense_card = _StatCard("EXPENSE", "—", "#a6e3a1")
        self._not_expense_card = _StatCard("NOT_EXPENSE", "—", "#f38ba8")
        
        stats_row.addWidget(self._total_card)
        stats_row.addWidget(self._expense_card)
        stats_row.addWidget(self._not_expense_card)
        stats_row.addStretch()
        
        layout.addLayout(stats_row)

        # ── Model performance section ───────────────────────────────────────
        perf_frame = QFrame()
        perf_frame.setObjectName("perfFrame")
        perf_layout = QHBoxLayout(perf_frame)
        perf_layout.setContentsMargins(12, 8, 12, 8)
        
        perf_title = QLabel("Model Performance")
        perf_title.setStyleSheet(f"color: {TEXT}; font-weight: bold;")
        perf_layout.addWidget(perf_title)
        
        self._accuracy_label = QLabel("Accuracy: —")
        self._accuracy_label.setStyleSheet(f"color: {SUCCESS};")
        perf_layout.addWidget(self._accuracy_label)
        
        self._f1_label = QLabel("F1-Score: —")
        self._f1_label.setStyleSheet(f"color: {TEXT_DIM};")
        perf_layout.addWidget(self._f1_label)
        
        perf_layout.addStretch()
        
        # Retrain button
        self._retrain_btn = QPushButton("🧠 Retrain Model")
        self._retrain_btn.setObjectName("primaryBtn")
        self._retrain_btn.clicked.connect(self._on_retrain_clicked)
        perf_layout.addWidget(self._retrain_btn)
        
        layout.addWidget(perf_frame)

        # ── Progress bar (hidden by default) ────────────────────────────────
        self._progress_frame = QFrame()
        self._progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self._progress_frame)
        progress_layout.setContentsMargins(0, 4, 0, 8)
        
        self._progress_label = QLabel("Training...")
        self._progress_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        progress_layout.addWidget(self._progress_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)
        
        # Cancel button
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setMaximumWidth(80)
        self._cancel_btn.clicked.connect(self._on_cancel_training)
        progress_layout.addWidget(self._cancel_btn)
        
        layout.addWidget(self._progress_frame)

        # ── Add Sample button ───────────────────────────────────────────────
        add_sample_btn = QPushButton("➕ Add Training Sample")
        add_sample_btn.setObjectName("secondaryBtn")
        add_sample_btn.clicked.connect(self._on_add_sample)
        layout.addWidget(add_sample_btn)

        # ── Search bar ───────────────────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Search training data (subject, sender, label)…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filters)
        layout.addWidget(self._search)

        # ── Preview table ────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(CI["#"], QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(CI["Subject"], QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["Sender"], QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(CI["Label"], QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self._table, stretch=1)

        # ── Summary label ───────────────────────────────────────────────────
        self._summary_label = QLabel("Loading...")
        self._summary_label.setObjectName("statusLabel")
        self._summary_label.setStyleSheet(f"color: {TEXT_DIM};")
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._summary_label)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_data_async(self) -> None:
        """Load training data in background thread."""
        if self._load_worker and self._load_worker.isRunning():
            return
        
        self._load_worker = TrainingDataLoadWorker(limit=50, parent=self)
        self._load_worker.finished.connect(self._on_data_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_data_loaded(self, rows: list[dict]) -> None:
        """Handle loaded training data."""
        self._all_rows = rows
        self._apply_filters()

    def _on_load_error(self, msg: str) -> None:
        """Handle load error."""
        logger.error("Failed to load training data: %s", msg)

    def _refresh_all(self) -> None:
        """Refresh all data."""
        self._refresh_stats()
        self._load_data_async()

    def _refresh_stats(self) -> None:
        """Refresh statistics display."""
        stats = get_training_data_stats()
        
        self._total_card.set_value(str(stats["total_rows"]))
        self._expense_card.set_value(f"{stats['expense_count']} ({stats['expense_pct']}%)")
        self._not_expense_card.set_value(f"{stats['not_expense_count']} ({stats['not_expense_pct']}%)")

    # ── Filter logic ────────────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        """Apply search filter to training data."""
        query = self._search.text().strip().lower()
        
        if not query:
            self._visible_rows = list(self._all_rows)
        else:
            self._visible_rows = []
            for row in self._all_rows:
                haystack = " ".join([
                    row.get("subject", ""),
                    row.get("sender", ""),
                    row.get("label", ""),
                ]).lower()
                if query in haystack:
                    self._visible_rows.append(row)
        
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate table with visible rows."""
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._visible_rows))
        
        for r, row in enumerate(self._visible_rows):
            label = row.get("label", "UNKNOWN")
            is_expense = label == "EXPENSE"
            
            # Create label badge
            if is_expense:
                label_badge = f"<span style='background:{SUCCESS_BG};color:{SUCCESS};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600'>{label}</span>"
            else:
                label_badge = f"<span style='background:{WARNING_BG};color:{WARNING};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600'>{label}</span>"
            
            items = [
                _item(str(r + 1), CI["#"], center=True),
                _item(_trunc(row.get("subject", ""), 50), CI["Subject"]),
                _item(_trunc(row.get("sender", ""), 30), CI["Sender"]),
                _item(label_badge, CI["Label"]),
            ]
            
            for col, item in enumerate(items):
                self._table.setItem(r, col, item)
        
        self._table.blockSignals(False)
        self._update_summary_label()

    def _update_summary_label(self) -> None:
        """Update summary label with row counts."""
        total = len(self._all_rows)
        visible = len(self._visible_rows)
        
        if total == 0:
            self._summary_label.setText("No training data")
        else:
            self._summary_label.setText(f"Showing {visible} of {total} rows")

    # ── Training operations ────────────────────────────────────────────────────

    def _on_retrain_clicked(self) -> None:
        """Handle retrain button click."""
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Training in Progress", "Training is already running.")
            return
        
        # Ask for retrain options
        dlg = _RetrainDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Start training worker
        self._start_training(
            retrain_with_feedback=dlg.retrain_with_feedback(),
            distilbert=dlg.use_distilbert()
        )

    def _start_training(
        self, retrain_with_feedback: bool = False, distilbert: bool = False
    ) -> None:
        """Start training worker."""
        self._retrain_btn.setEnabled(False)
        self._progress_frame.setVisible(True)
        self._progress_bar.setValue(0)
        
        self._worker = TrainingWorker(
            retrain_with_feedback=retrain_with_feedback,
            distilbert=distilbert,
            parent=self,
        )
        self._worker.progress.connect(self._on_training_progress)
        self._worker.finished.connect(self._on_training_finished)
        self._worker.error.connect(self._on_training_error)
        self._worker.start()

    def _on_training_progress(self, percent: int, message: str) -> None:
        """Handle training progress update."""
        self._progress_bar.setValue(percent)
        self._progress_label.setText(message)

    def _on_training_finished(self, metrics: dict) -> None:
        """Handle training completion."""
        self._progress_frame.setVisible(False)
        self._retrain_btn.setEnabled(True)
        self._worker = None
        
        # Update performance metrics
        self._accuracy_label.setText(f"Accuracy: {metrics.get('accuracy', '—')}")
        self._f1_label.setText(f"F1-Score: EXP={metrics.get('f1_expense', '—')} NOT_EXP={metrics.get('f1_not_expense', '—')}")
        
        # Refresh stats and data
        self._refresh_all()
        
        QMessageBox.information(
            self,
            "Training Complete",
            f"Model retrained successfully!\n\n"
            f"Accuracy: {metrics.get('accuracy', '—')}\n"
            f"Support: {metrics.get('support', 0)} samples"
        )

    def _on_training_error(self, error_msg: str) -> None:
        """Handle training error."""
        self._progress_frame.setVisible(False)
        self._retrain_btn.setEnabled(True)
        self._worker = None
        
        QMessageBox.critical(self, "Training Failed", error_msg)

    def _on_cancel_training(self) -> None:
        """Cancel training."""
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._cancel_btn.setEnabled(False)
            self._cancel_btn.setText("Cancelling...")

    # ── Add sample ───────────────────────────────────────────────────────────

    def _on_add_sample(self) -> None:
        """Show add sample dialog."""
        dlg = _AddSampleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            subject = dlg.get_subject()
            body = dlg.get_body()
            sender = dlg.get_sender()
            label = dlg.get_label()
            
            try:
                count = add_training_sample(subject, body, sender, label)
                self._refresh_all()
                QMessageBox.information(
                    self,
                    "Sample Added",
                    f"Training sample added successfully.\n\nTotal samples: {count}"
                )
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to add sample: {exc}")

    # ── Download dropdown ─────────────────────────────────────────────────────

    def _on_download_clicked(self) -> None:
        """Show download menu."""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        # Export current training data
        export_current = menu.addAction("📄 Export Current Training Data")
        export_current.triggered.connect(self._export_current_data)
        
        menu.addSeparator()
        
        # List available backups
        backups = list_backups()
        if backups:
            backup_menu = menu.addMenu("📦 Download Backup")
            for backup in backups:
                action = backup_menu.addAction(
                    f"{backup['created_at']} ({backup['size_mb']} MB)"
                )
                action.setData(backup["path"])
                action.triggered.connect(lambda _, p=backup["path"]: self._export_backup(p))
        else:
            no_backups = menu.addAction("No backups available")
            no_backups.setEnabled(False)
        
        menu.addSeparator()
        
        # Export database
        export_db = menu.addAction("💾 Export Expenses Database")
        export_db.triggered.connect(self._export_database)
        
        # Import from CSV
        import_csv = menu.addAction("📥 Import from CSV")
        import_csv.triggered.connect(self._import_from_csv)
        
        menu.exec(self._download_btn.mapToGlobal(self._download_btn.rect().bottomLeft()))

    def _export_current_data(self) -> None:
        """Export current training data."""
        try:
            path = export_training_data(Path("data/training_emails.csv"))
            QMessageBox.information(self, "Export Complete", f"Training data exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Failed to export: {exc}")

    def _export_backup(self, backup_path: str) -> None:
        """Copy backup to data directory."""
        try:
            import shutil
            src = Path(backup_path)
            dst = Path("data") / src.name
            shutil.copy2(src, dst)
            QMessageBox.information(self, "Export Complete", f"Backup exported to:\n{dst}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Failed to export backup: {exc}")

    def _export_database(self) -> None:
        """Export expenses database."""
        if not self._db_path or not self._db_path.exists():
            QMessageBox.warning(self, "Database Not Found", "No database available for export.")
            return
        
        try:
            path = export_database(self._db_path)
            QMessageBox.information(self, "Export Complete", f"Database exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Failed to export database: {exc}")

    def _import_from_csv(self) -> None:
        """Import training data from CSV."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Training Data",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not path:
            return
        
        # Ask if merge or replace
        reply = QMessageBox.question(
            self,
            "Import Options",
            "Merge with existing data or replace?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        try:
            merge = (reply == QMessageBox.StandardButton.Yes)
            count = import_training_data(Path(path), merge=merge)
            self._refresh_all()
            QMessageBox.information(
                self,
                "Import Complete",
                f"Training data imported successfully.\n\nTotal samples: {count}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", f"Failed to import: {exc}")


# ── Helper widgets ────────────────────────────────────────────────────────────

class _StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(70)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        self._label = QLabel(label)
        self._label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._label)
        
        self._value = QLabel(value)
        self._value.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        layout.addWidget(self._value)
    
    def set_value(self, value: str) -> None:
        self._value.setText(value)


class _RetrainDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Retrain Model")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("Select training options:"))
        
        self._retrain_feedback = QCheckBox("Retrain with feedback data")
        self._retrain_feedback.setChecked(False)
        self._retrain_feedback.setToolTip("Merge user feedback from review queue before training")
        layout.addWidget(self._retrain_feedback)
        
        self._use_distilbert = QCheckBox("Fine-tune DistilBERT")
        self._use_distilbert.setChecked(False)
        self._use_distilbert.setToolTip("Train DistilBERT model (slower, more accurate)")
        layout.addWidget(self._use_distilbert)
        
        btns = QDialogButtonBox(
            QDialog.StandardButton.Ok | QDialogDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
    
    def retrain_with_feedback(self) -> bool:
        return self._retrain_feedback.isChecked()
    
    def use_distilbert(self) -> bool:
        return self._use_distilbert.isChecked()


class _AddSampleDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Training Sample")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Subject
        layout.addWidget(QLabel("Subject:"))
        self._subject = QLineEdit()
        self._subject.setPlaceholderText("Email subject line...")
        layout.addWidget(self._subject)
        
        # Sender
        layout.addWidget(QLabel("Sender:"))
        self._sender = QLineEdit()
        self._sender.setPlaceholderText("sender@example.com")
        layout.addWidget(self._sender)
        
        # Body
        layout.addWidget(QLabel("Body:"))
        self._body = QLineEdit()
        self._body.setPlaceholderText("Email body text (first 3000 chars used)...")
        layout.addWidget(self._body)
        
        # Label
        layout.addWidget(QLabel("Label:"))
        label_layout = QHBoxLayout()
        self._expense_radio = QCheckBox("EXPENSE")
        self._expense_radio.setChecked(True)
        self._not_expense_radio = QCheckBox("NOT_EXPENSE")
        
        self._expense_radio.toggled.connect(self._on_expense_toggled)
        self._not_expense_radio.toggled.connect(self._on_not_expense_toggled)
        
        label_layout.addWidget(self._expense_radio)
        label_layout.addWidget(self._not_expense_radio)
        label_layout.addStretch()
        layout.addLayout(label_layout)
        
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
    
    def _on_expense_toggled(self, checked: bool) -> None:
        if checked:
            self._not_expense_radio.setChecked(False)
    
    def _on_not_expense_toggled(self, checked: bool) -> None:
        if checked:
            self._expense_radio.setChecked(False)
    
    def get_subject(self) -> str:
        return self._subject.text().strip()
    
    def get_body(self) -> str:
        return self._body.text().strip()
    
    def get_sender(self) -> str:
        return self._sender.text().strip()
    
    def get_label(self) -> str:
        return "EXPENSE" if self._expense_radio.isChecked() else "NOT_EXPENSE"


def _item(text: str, col: int, center: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if center:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    else:
        it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return it


def _trunc(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n - 1] + "…"
