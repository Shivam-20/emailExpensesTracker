"""
main.py — Application entry point.
Handles first-run setup dialog, then launches MainWindow.
"""

import json
import logging
import sys
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from styles import configure_ctk_theme, ACCENT, TEXT, TEXT_DIM, SURFACE, BORDER_BRIGHT, BG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_BOOTSTRAP_FILE = Path.home() / ".expense-tracker-path"
_DEFAULT_DATA_DIR = Path.home() / ".config" / "expense-tracker"


def get_data_dir() -> Path:
    """Return the user's chosen data directory, or None if not set yet."""
    if _BOOTSTRAP_FILE.exists():
        try:
            path = Path(_BOOTSTRAP_FILE.read_text().strip())
            if path.exists():
                return path
        except OSError:
            pass
    return None


def _save_bootstrap_path(path: Path) -> None:
    _BOOTSTRAP_FILE.write_text(str(path))


# ── First-run dialog ──────────────────────────────────────────────────────────

class FirstRunDialog(ctk.CTkToplevel):
    """Modal shown on first launch to let user choose where to store app data."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("Welcome to Expense Tracker")
        self.geometry("460x320")
        self.resizable(False, False)
        self.grab_set()           # make modal
        self.focus_set()
        self.transient(parent)

        self._chosen_path: Path = Path.home() / "expense-tracker-data"
        self._radio_var = ctk.StringVar(value="default")
        self._result: Path | None = None

        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)    # block until closed

    def _setup_ui(self) -> None:
        self.configure(fg_color=BG)
        pad = {"padx": 24, "pady": 0}

        # Title
        ctk.CTkLabel(
            self, text="💰  Welcome to Expense Tracker",
            font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
            text_color=ACCENT,
        ).pack(pady=(20, 4), **pad)

        ctk.CTkLabel(
            self,
            text="Where should we store your app data?\n(SQLite database, Gmail token, settings)",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=TEXT_DIM,
            justify="center",
        ).pack(pady=(0, 14))

        # Radio options
        options = [
            ("default",   f"~/.config/expense-tracker/  (recommended)"),
            ("script",    "Same folder as this script"),
            ("custom",    "Browse…"),
        ]
        for value, label in options:
            ctk.CTkRadioButton(
                self,
                text=label,
                variable=self._radio_var,
                value=value,
                command=self._on_radio,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=TEXT,
                fg_color=ACCENT,
                hover_color=ACCENT,
                border_color=BORDER_BRIGHT,
            ).pack(anchor="w", padx=36, pady=3)

        # Browse button
        self._browse_btn = ctk.CTkButton(
            self,
            text="Browse…",
            command=self._browse,
            font=ctk.CTkFont(family="Inter", size=12),
            state="disabled",
            fg_color=SURFACE,
            hover_color=BORDER_BRIGHT,
            text_color=TEXT,
            border_color=BORDER_BRIGHT,
            border_width=1,
            corner_radius=8,
        )
        self._browse_btn.pack(anchor="w", padx=70, pady=(4, 0))

        # Path label
        self._path_lbl = ctk.CTkLabel(
            self, text="", text_color=TEXT_DIM,
            font=ctk.CTkFont(family="Inter", size=10),
        )
        self._path_lbl.pack(pady=(4, 0))

        # Get Started button
        ctk.CTkButton(
            self,
            text="Get Started →",
            command=self._on_accept,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            corner_radius=8,
            fg_color=ACCENT,
            hover_color=ACCENT,
            text_color="#1e1e2e",
        ).pack(pady=(16, 20), ipadx=20, ipady=4)

    def _on_radio(self) -> None:
        is_custom = self._radio_var.get() == "custom"
        self._browse_btn.configure(state="normal" if is_custom else "disabled")

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(title="Choose Data Directory")
        if chosen:
            self._chosen_path = Path(chosen)
            self._path_lbl.configure(text=str(self._chosen_path))

    def _on_accept(self) -> None:
        val = self._radio_var.get()
        if val == "default":
            self._result = _DEFAULT_DATA_DIR
        elif val == "script":
            self._result = Path(__file__).parent
        else:
            self._result = self._chosen_path
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()

    def chosen_path(self) -> Path | None:
        return self._result


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    configure_ctk_theme()

    root = ctk.CTk()
    root.withdraw()   # hide root temporarily while checking data dir

    data_dir = get_data_dir()
    if data_dir is None:
        dlg = FirstRunDialog(root)
        data_dir = dlg.chosen_path()
        if data_dir is None:
            root.destroy()
            sys.exit(0)
        data_dir.mkdir(parents=True, exist_ok=True)
        _save_bootstrap_path(data_dir)

    data_dir.mkdir(parents=True, exist_ok=True)

    from main_window import MainWindow
    window = MainWindow(root, data_dir)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
