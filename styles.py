"""
styles.py — Global dark theme palette and QSS stylesheets for v2.
Catppuccin-Mocha inspired with improved responsiveness and polish.
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# ── Colour tokens ─────────────────────────────────────────────────────────────
BG             = "#0f0f1a"
SIDEBAR_BG     = "#0a0a12"
SURFACE        = "#1e1e2e"
SURFACE_HOVER  = "#313244"
SURFACE_ACTIVE = "#45475a"
SURFACE2       = "#16162a"
SURFACE3       = "#313244"
ACCENT         = "#cba6f7"
ACCENT_LIGHT   = "#d9c4f5"
ACCENT_DARK    = "#a682d8"
ACCENT_DK      = "#a682d8"
TEXT           = "#cdd6f4"
TEXT_DIM       = "#6c7086"
TEXT_MUTE      = "#45475a"
SUCCESS        = "#a6e3a1"
SUCCESS_BG     = "#1e3a26"
WARNING        = "#fab387"
WARNING_BG     = "#3a3528"
ERROR          = "#f38ba8"
ERROR_BG       = "#3a2628"
INFO           = "#89b4fa"
INFO_BG        = "#1e3a5a"
BORDER         = "#313244"
BORDER_BRIGHT  = "#45475a"
AMBER          = "#f9e2af"

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY    = "'Inter', 'Segoe UI', 'DejaVu Sans', sans-serif"
FONT_SIZE_BASE = "13px"
FONT_SIZE_SM   = "11px"
FONT_SIZE_XS   = "10px"
FONT_SIZE_LG   = "15px"
FONT_SIZE_XL   = "18px"
FONT_SIZE_XXL  = "24px"

# ── Spacing ──────────────────────────────────────────────────────────────────
SPACING_XS  = "4px"
SPACING_SM  = "8px"
SPACING_MD  = "12px"
SPACING_LG  = "16px"
SPACING_XL  = "20px"
SPACING_XXL = "24px"

# ── Border Radius ─────────────────────────────────────────────────────────────
RADIUS_SM   = "4px"
RADIUS_MD   = "8px"
RADIUS_LG   = "12px"
RADIUS_XL   = "16px"
RADIUS_FULL = "9999px"

# ── Shadows ────────────────────────────────────────────────────────────────────
SHADOW_SM = "rgba(0, 0, 0, 0.3)"
SHADOW_MD = "rgba(0, 0, 0, 0.5)"
SHADOW_LG = "rgba(0, 0, 0, 0.7)"

# ── Category Colors ───────────────────────────────────────────────────────────
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

# ── Confidence Colors & Badges ────────────────────────────────────────────────
CONFIDENCE_COLORS = {
    "HIGH":   SUCCESS,
    "MEDIUM": AMBER,
    "LOW":    ERROR,
    "NONE":   TEXT_DIM,
}

CONFIDENCE_BADGES = {
    "HIGH":   (SUCCESS_BG, SUCCESS),
    "MEDIUM": (WARNING_BG, WARNING),
    "LOW":    (ERROR_BG, ERROR),
    "NONE":   (SURFACE, TEXT_MUTE),
}


# ── Theme Application ────────────────────────────────────────────────────────
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


# ── QSS Stylesheet ─────────────────────────────────────────────────────────────
MAIN_STYLE = f"""

/* ━━━━━━━━━━━━━━━━  BASE  ━━━━━━━━━━━━━━━━ */
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_BASE};
    color: {TEXT};
    background-color: {BG};
}}
QMainWindow, QDialog {{ background-color: {BG}; }}

/* ── Tooltip ── */
QToolTip {{
    background-color: {SURFACE3};
    color: {TEXT};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_SM};
    padding: 6px 10px;
    font-size: {FONT_SIZE_SM};
}}

/* ━━━━━━━━━━━━━━━━  SIDEBAR  ━━━━━━━━━━━━━━━━ */
#sidebar {{
    background-color: {SIDEBAR_BG};
    border-right: 1px solid {BORDER};
}}
#appTitle {{
    font-size: {FONT_SIZE_XL};
    font-weight: bold;
    color: {ACCENT};
    padding: 6px 0 4px 0;
}}
#accountPill {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_FULL};
    padding: 4px 12px;
    color: {TEXT_DIM};
    font-size: {FONT_SIZE_SM};
}}
#accountPill[connected="true"] {{
    background-color: {SUCCESS_BG};
    border-color: {SUCCESS};
    color: {SUCCESS};
}}

/* Section labels — objectName="sectionLabel" */
#sectionLabel {{
    color: {TEXT_DIM};
    font-size: {FONT_SIZE_XS};
    font-weight: 700;
    padding: 2px 0 2px 7px;
    border-left: 2px solid {ACCENT_DARK};
}}

/* ━━━━━━━━━━━━━━━━  BUTTONS  ━━━━━━━━━━━━━━━━ */
QPushButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_MD};
    padding: 6px 14px;
    min-height: 30px;
    font-size: {FONT_SIZE_BASE};
}}
QPushButton:focus  {{ outline: none; border-color: {ACCENT}; }}
QPushButton:hover  {{ background-color: {SURFACE_HOVER}; border-color: {ACCENT_DARK}; }}
QPushButton:pressed {{ background-color: {SURFACE_ACTIVE}; }}
QPushButton:disabled {{ color: {TEXT_MUTE}; border-color: {SURFACE}; background-color: {SURFACE}; }}

#primaryBtn {{
    background-color: {ACCENT};
    color: #1e1e2e;
    font-weight: 700;
    border: none;
    min-height: 34px;
    padding: 7px 16px;
    border-radius: {RADIUS_MD};
}}
#primaryBtn:hover   {{ background-color: {ACCENT_LIGHT}; }}
#primaryBtn:pressed {{ background-color: {ACCENT_DARK}; color: #ffffff; }}
#primaryBtn:focus   {{ outline: none; border: 1px solid {ACCENT_LIGHT}; }}

#ghostBtn {{
    background: transparent;
    border: 1px solid {ACCENT_DARK};
    color: {ACCENT};
    min-height: 28px;
    padding: 5px 12px;
}}
#ghostBtn:hover   {{ background-color: rgba(203,166,247,0.12); border-color: {ACCENT}; }}
#ghostBtn:pressed {{ background-color: rgba(203,166,247,0.22); }}
#ghostBtn:focus   {{ outline: none; }}

#dangerBtn {{
    background-color: {ERROR_BG};
    color: {ERROR};
    border: 1px solid {ERROR};
}}
#dangerBtn:hover {{ background-color: {ERROR}; color: #ffffff; }}

/* ━━━━━━━━━━━━━━━━  CHIPS  ━━━━━━━━━━━━━━━━ */
#chipActive {{
    background-color: {ACCENT};
    color: #1e1e2e;
    border: none;
    border-radius: {RADIUS_FULL};
    padding: 3px 10px;
    font-size: {FONT_SIZE_SM};
    font-weight: 600;
    min-height: 24px;
}}
#chipInactive {{
    background-color: {SURFACE};
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_FULL};
    padding: 3px 10px;
    font-size: {FONT_SIZE_SM};
    min-height: 24px;
}}
#chipInactive:hover {{ background-color: {SURFACE_HOVER}; color: {TEXT}; border-color: {ACCENT_DARK}; }}

/* ━━━━━━━━━━━━━━━━  INPUT CONTROLS  ━━━━━━━━━━━━━━━━ */
QComboBox, QLineEdit, QSpinBox, QDateEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_SM};
    padding: 4px 8px;
    color: {TEXT};
    min-height: 26px;
    selection-background-color: {ACCENT};
    selection-color: #1e1e2e;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDateEdit:focus {{
    outline: none;
    border-color: {ACCENT};
    background-color: {SURFACE_HOVER};
}}
QComboBox:hover, QSpinBox:hover, QDateEdit:hover {{
    border-color: {ACCENT_DARK};
}}

/* Drop-down arrow area */
QComboBox::drop-down, QDateEdit::drop-down {{
    border: none;
    width: 22px;
    border-left: 1px solid {BORDER};
}}
QComboBox::down-arrow, QDateEdit::down-arrow {{
    width: 8px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: #1e1e2e;
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_SM};
    padding: 2px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 5px 10px;
    min-height: 26px;
    border-radius: {RADIUS_SM};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {ACCENT};
    color: #1e1e2e;
}}

/* SpinBox buttons */
QSpinBox::up-button, QSpinBox::down-button {{
    border: none;
    width: 18px;
    background-color: {SURFACE};
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {SURFACE_HOVER};
}}

/* Calendar popup for QDateEdit */
QCalendarWidget {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_MD};
}}
QCalendarWidget QToolButton {{
    background-color: transparent;
    color: {ACCENT};
    font-weight: bold;
    border: none;
    padding: 4px 8px;
    min-height: 26px;
}}
QCalendarWidget QToolButton:hover {{ background-color: {SURFACE_HOVER}; border-radius: {RADIUS_SM}; }}
QCalendarWidget QMenu {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_BRIGHT};
}}
QCalendarWidget QSpinBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_BRIGHT};
    color: {TEXT};
    font-weight: bold;
}}
QCalendarWidget QAbstractItemView:enabled {{
    background-color: {SURFACE};
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: #1e1e2e;
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {TEXT_MUTE}; }}

/* ━━━━━━━━━━━━━━━━  TABLE  ━━━━━━━━━━━━━━━━ */
QTableWidget {{
    background-color: {SURFACE};
    alternate-background-color: {SURFACE2};
    gridline-color: {BORDER};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    selection-background-color: rgba(203,166,247,0.25);
    selection-color: {TEXT};
    outline: none;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}
QTableWidget::item:selected {{
    background-color: rgba(203,166,247,0.18);
    color: {TEXT};
}}
QTableWidget::item:hover {{
    background-color: {SURFACE_HOVER};
}}

QHeaderView::section {{
    background-color: {SURFACE2};
    color: {TEXT_DIM};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 2px solid {BORDER_BRIGHT};
    padding: 7px 10px;
    font-weight: 700;
    font-size: {FONT_SIZE_XS};
}}
QHeaderView::section:hover {{ background-color: {SURFACE_HOVER}; color: {TEXT}; }}
QHeaderView {{
    background-color: {SURFACE2};
}}
QHeaderView::section:first {{ border-top-left-radius: {RADIUS_SM}; }}
QHeaderView::section:last  {{ border-top-right-radius: {RADIUS_SM}; border-right: none; }}

/* ━━━━━━━━━━━━━━━━  TABS  ━━━━━━━━━━━━━━━━ */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG};
    border-radius: {RADIUS_MD};
    border-top-left-radius: 0;
    margin-top: -1px;
    padding: {SPACING_MD};
}}
QTabBar::tab {{
    background-color: {SURFACE2};
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 2px;
    margin-top: 4px;
    border-top-left-radius: {RADIUS_SM};
    border-top-right-radius: {RADIUS_SM};
    font-size: {FONT_SIZE_SM};
    font-weight: 500;
    min-width: 110px;
}}
QTabBar::tab:selected {{
    background-color: {BG};
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background-color: {SURFACE_HOVER};
    color: {TEXT};
    border-bottom: 1px solid {ACCENT_DARK};
}}

/* ━━━━━━━━━━━━━━━━  SCROLLBARS  ━━━━━━━━━━━━━━━━ */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_BRIGHT};
    border-radius: 4px;
    min-height: 24px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DARK}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_BRIGHT};
    border-radius: 4px;
    min-width: 24px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT_DARK}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ━━━━━━━━━━━━━━━━  PROGRESS BAR  ━━━━━━━━━━━━━━━━ */
QProgressBar {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    height: 6px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_DARK}, stop:1 {ACCENT});
    border-radius: {RADIUS_SM};
}}

/* ━━━━━━━━━━━━━━━━  CARDS  ━━━━━━━━━━━━━━━━ */
#summaryCard {{
    background-color: {SURFACE2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD};
    padding: 2px;
}}
#summaryValue {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 700;
}}
#cardLabel {{
    color: {TEXT_DIM};
    font-size: {FONT_SIZE_XS};
    font-weight: 600;
}}
#cardValue {{
    color: {TEXT};
    font-size: {FONT_SIZE_LG};
    font-weight: 700;
}}

/* ━━━━━━━━━━━━━━━━  MISC  ━━━━━━━━━━━━━━━━ */
#separator {{
    background-color: {BORDER};
    max-height: 1px;
    min-height: 1px;
    margin: 2px 0;
}}
#statusLabel {{
    color: {TEXT_DIM};
    font-size: {FONT_SIZE_SM};
}}
QStatusBar {{
    background-color: {SIDEBAR_BG};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: {FONT_SIZE_SM};
    padding: 2px 6px;
}}
QStatusBar::item {{ border: none; }}

QMessageBox {{
    background-color: {SURFACE};
}}
QMessageBox QLabel {{ color: {TEXT}; }}
QMessageBox QPushButton {{ min-width: 80px; }}

#bulkBar {{
    background-color: rgba(166,130,216,0.18);
    border-top: 1px solid {ACCENT_DARK};
    border-bottom: 1px solid {ACCENT_DARK};
}}

QMenu {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_SM};
    padding: 4px;
    color: {TEXT};
}}
QMenu::item {{
    padding: 6px 28px 6px 12px;
    border-radius: {RADIUS_SM};
}}
QMenu::item:selected {{ background-color: {SURFACE_HOVER}; color: {TEXT}; }}
QMenu::indicator {{ width: 14px; height: 14px; margin-left: 6px; }}

QCheckBox {{
    spacing: 8px;
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_BRIGHT};
    border-radius: {RADIUS_SM};
    background: {SURFACE};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT_DARK}; }}

QLabel#fetchHint {{
    color: {TEXT_MUTE};
    font-size: {FONT_SIZE_XS};
}}
"""
