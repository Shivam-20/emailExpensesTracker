"""
styles.py — Global dark theme palette and QSS stylesheets for v2.
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# ── Colour tokens ─────────────────────────────────────────────────────────────
BG         = "#1e1e2e"
SIDEBAR_BG = "#13131f"
SURFACE    = "#2a2a3e"
SURFACE2   = "#16162a"
SURFACE3   = "#313244"
ACCENT     = "#7c6af7"
ACCENT_DK  = "#5a4ed1"
TEXT       = "#cdd6f4"
TEXT_DIM   = "#6c7086"
SUCCESS    = "#a6e3a1"
WARNING    = "#fab387"
ERROR      = "#f38ba8"
BORDER     = "#45475a"
AMBER      = "#f9e2af"

CATEGORY_COLORS: dict[str, str] = {
    "Shopping":      "#89b4fa",
    "Food":          "#fab387",
    "Transport":     "#a6e3a1",
    "Subscriptions": "#cba6f7",
    "Utilities":     "#94e2d5",
    "Telecom":       "#89dceb",
    "Healthcare":    "#f38ba8",
    "Travel":        "#f9e2af",
    "Insurance":     "#b4befe",
    "Finance":       "#eba0ac",
    "Other":         "#6c7086",
}

CONFIDENCE_COLORS = {
    "HIGH":   SUCCESS,
    "MEDIUM": AMBER,
    "LOW":    ERROR,
    "NONE":   TEXT_DIM,
}


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    p = QPalette()
    c = QColor
    p.setColor(QPalette.ColorRole.Window,          c(BG))
    p.setColor(QPalette.ColorRole.WindowText,      c(TEXT))
    p.setColor(QPalette.ColorRole.Base,            c(SURFACE))
    p.setColor(QPalette.ColorRole.AlternateBase,   c(SURFACE2))
    p.setColor(QPalette.ColorRole.ToolTipBase,     c(SURFACE))
    p.setColor(QPalette.ColorRole.ToolTipText,     c(TEXT))
    p.setColor(QPalette.ColorRole.Text,            c(TEXT))
    p.setColor(QPalette.ColorRole.Button,          c(SURFACE))
    p.setColor(QPalette.ColorRole.ButtonText,      c(TEXT))
    p.setColor(QPalette.ColorRole.BrightText,      c(ERROR))
    p.setColor(QPalette.ColorRole.Link,            c(ACCENT))
    p.setColor(QPalette.ColorRole.Highlight,       c(ACCENT))
    p.setColor(QPalette.ColorRole.HighlightedText, c("#ffffff"))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       c(TEXT_DIM))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, c(TEXT_DIM))
    app.setPalette(p)


MAIN_STYLE = """
QWidget {
    font-family: 'Inter', 'Segoe UI', 'DejaVu Sans', sans-serif;
    font-size: 13px;
    color: """ + TEXT + """;
    background-color: """ + BG + """;
}
QMainWindow, QDialog { background-color: """ + BG + """; }
#sidebar {
    background-color: """ + SIDEBAR_BG + """;
    border-right: 1px solid """ + BORDER + """;
}
#appTitle { font-size: 16px; font-weight: bold; color: """ + ACCENT + """; padding: 8px 0 2px 0; }
#accountPill {
    background-color: """ + SURFACE3 + """;
    border-radius: 10px; padding: 3px 10px;
    color: """ + SUCCESS + """; font-size: 11px;
}
QPushButton {
    background-color: """ + SURFACE + """;
    color: """ + TEXT + """;
    border: 1px solid """ + BORDER + """;
    border-radius: 7px; padding: 6px 14px;
}
QPushButton:hover  { background-color: """ + SURFACE3 + """; border-color: """ + ACCENT + """; }
QPushButton:pressed { background-color: """ + ACCENT_DK + """; }
QPushButton:disabled { color: """ + TEXT_DIM + """; border-color: """ + SURFACE + """; }
#primaryBtn {
    background-color: """ + ACCENT + """;
    color: #ffffff; font-weight: bold; border: none; padding: 8px 16px;
}
#primaryBtn:hover  { background-color: """ + ACCENT_DK + """; }
#primaryBtn:pressed { background-color: #4a3faa; }
#ghostBtn { background: transparent; border: 1px solid """ + ACCENT + """; color: """ + ACCENT + """; }
#ghostBtn:hover { background-color: """ + ACCENT + """; color: #ffffff; }
#chipActive {
    background-color: """ + ACCENT + """;
    color: #ffffff; border: none; border-radius: 12px; padding: 3px 10px; font-size: 11px;
}
#chipInactive {
    background-color: """ + SURFACE + """;
    color: #888888; border: none; border-radius: 12px; padding: 3px 10px; font-size: 11px;
}
#chipInactive:hover { background-color: """ + SURFACE3 + """; color: """ + TEXT + """; }
QComboBox {
    background-color: """ + SURFACE + """; border: 1px solid """ + BORDER + """;
    border-radius: 5px; padding: 5px 10px; color: """ + TEXT + """;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: """ + SURFACE + """; color: """ + TEXT + """;
    selection-background-color: """ + ACCENT + """;
}
QLineEdit, QSpinBox {
    background-color: """ + SURFACE + """; border: 1px solid """ + BORDER + """;
    border-radius: 5px; padding: 6px 10px; color: """ + TEXT + """;
}
QLineEdit:focus, QSpinBox:focus { border-color: """ + ACCENT + """; }
QTableWidget {
    background-color: """ + SURFACE2 + """; alternate-background-color: """ + SURFACE + """;
    gridline-color: """ + SURFACE + """; color: """ + TEXT + """; border: none;
}
QTableWidget::item { padding: 4px 8px; }
QTableWidget::item:selected { background-color: """ + ACCENT + """; color: #ffffff; }
QHeaderView::section {
    background-color: """ + SURFACE3 + """; color: """ + TEXT + """;
    border: none; border-right: 1px solid """ + BORDER + """;
    border-bottom: 1px solid """ + BORDER + """;
    padding: 5px 8px; font-weight: bold; font-size: 12px;
}
QHeaderView::section:hover { background-color: """ + BORDER + """; }
QTabWidget::pane { border: 1px solid """ + BORDER + """; background-color: """ + SURFACE2 + """; }
QTabBar::tab {
    background-color: """ + SURFACE + """; color: """ + TEXT_DIM + """;
    border: 1px solid """ + BORDER + """; border-bottom: none;
    padding: 8px 18px; border-top-left-radius: 5px; border-top-right-radius: 5px; margin-right: 2px;
}
QTabBar::tab:selected { background-color: """ + SURFACE2 + """; color: """ + TEXT + """; border-bottom: 2px solid """ + ACCENT + """; }
QTabBar::tab:hover { background-color: """ + SURFACE3 + """; color: """ + TEXT + """; }
QScrollBar:vertical { background: """ + SURFACE2 + """; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: """ + BORDER + """; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: """ + ACCENT + """; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: """ + SURFACE2 + """; height: 8px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: """ + BORDER + """; border-radius: 4px; }
QProgressBar {
    background-color: """ + SURFACE + """; border: 1px solid """ + BORDER + """;
    border-radius: 3px; height: 6px; text-align: center; font-size: 0px;
}
QProgressBar::chunk { background-color: """ + ACCENT + """; border-radius: 3px; }
#summaryCard {
    background-color: """ + SURFACE3 + """; border: 1px solid """ + BORDER + """; border-radius: 8px; padding: 8px;
}
#cardLabel { color: """ + TEXT_DIM + """; font-size: 10px; }
#cardValue { color: """ + TEXT + """; font-size: 15px; font-weight: bold; }
#separator { background-color: """ + BORDER + """; max-height: 1px; min-height: 1px; }
#statusLabel { color: """ + TEXT_DIM + """; font-size: 11px; }
QStatusBar { background-color: """ + SIDEBAR_BG + """; color: """ + TEXT_DIM + """; border-top: 1px solid """ + BORDER + """; }
QMessageBox { background-color: """ + SURFACE + """; }
QMessageBox QLabel { color: """ + TEXT + """; }
#bulkBar { background-color: """ + ACCENT_DK + """; border-top: 1px solid """ + ACCENT + """; }
"""
