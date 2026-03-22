"""
main.py — Application entry point.
Handles first-run setup dialog, then launches MainWindow.
"""

import json
import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QDialogButtonBox,
    QFileDialog, QLabel, QMessageBox, QPushButton,
    QRadioButton, QVBoxLayout, QWidget,
)

from main_window import MainWindow
from styles import apply_dark_theme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_BOOTSTRAP_FILE = Path.home() / ".expense-tracker-path"
_DEFAULT_DATA_DIR = Path.home() / ".config" / "expense-tracker"


def get_data_dir() -> Path:
    """Return the user's chosen data directory, running first-run dialog if needed."""
    if _BOOTSTRAP_FILE.exists():
        try:
            path = Path(_BOOTSTRAP_FILE.read_text().strip())
            if path.exists():
                return path
        except OSError:
            pass
    return None


def run_first_run_dialog(app: QApplication) -> Path:
    """Show first-run setup dialog and return the chosen data directory."""
    dlg = FirstRunDialog()
    if dlg.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    path = dlg.chosen_path()
    path.mkdir(parents=True, exist_ok=True)
    _BOOTSTRAP_FILE.write_text(str(path))
    return path


class FirstRunDialog(QDialog):
    """
    Shown on first launch to let user choose where to store app data.
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to Expense Tracker")
        self.setMinimumWidth(440)
        self._custom_path: Path = Path.home() / "expense-tracker-data"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        hdr = QLabel("💰 Welcome to Expense Tracker")
        hdr.setStyleSheet("font-size: 17px; font-weight: bold;")
        layout.addWidget(hdr)

        layout.addWidget(QLabel("Where should we store your app data?\n(SQLite database, Gmail token, settings)"))

        self._grp = QButtonGroup(self)

        r1 = QRadioButton(f"  ~/.config/expense-tracker/  (recommended)")
        r1.setChecked(True)
        r2 = QRadioButton(f"  Same folder as this script")
        self._r_custom = QRadioButton("  Browse…")
        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.setEnabled(False)
        self._browse_btn.clicked.connect(self._browse)

        self._grp.addButton(r1, 0)
        self._grp.addButton(r2, 1)
        self._grp.addButton(self._r_custom, 2)
        self._grp.idClicked.connect(self._on_radio)

        for w in (r1, r2, self._r_custom):
            layout.addWidget(w)
        layout.addWidget(self._browse_btn)

        self._path_lbl = QLabel("")
        self._path_lbl.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._path_lbl)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Get Started →")
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)

    def _on_radio(self, btn_id: int) -> None:
        self._browse_btn.setEnabled(btn_id == 2)

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose Data Directory")
        if chosen:
            self._custom_path = Path(chosen)
            self._path_lbl.setText(str(self._custom_path))

    def chosen_path(self) -> Path:
        btn_id = self._grp.checkedId()
        if btn_id == 0:
            return _DEFAULT_DATA_DIR
        elif btn_id == 1:
            return Path(__file__).parent
        else:
            return self._custom_path


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Gmail Expense Tracker")
    app.setOrganizationName("ExpenseTracker")
    app.setApplicationVersion("2.0.0")

    font = QFont("Inter", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    apply_dark_theme(app)

    data_dir = get_data_dir()
    if data_dir is None:
        data_dir = run_first_run_dialog(app)

    data_dir.mkdir(parents=True, exist_ok=True)

    window = MainWindow(data_dir)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
