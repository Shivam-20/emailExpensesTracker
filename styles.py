"""
styles.py — Global dark theme palette and QSS stylesheets for v2.
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# ── Colour tokens ─────────────────────────────────────────────────────────────
BG           = "#0f0f1a"
SIDEBAR_BG   = "#0a0a12"
SURFACE      = "#1e1e2e"
SURFACE_HOVER = "#313244"
SURFACE_ACTIVE = "#45475a"
SURFACE2     = "#16162a"
SURFACE3     = "#313244"
ACCENT       = "#cba6f7"
ACCENT_LIGHT = "#d9c4f5"
ACCENT_DARK  = "#a682d8"
ACCENT_DK    = "#a682d8"
TEXT         = "#cdd6f4"
TEXT_DIM     = "#6c7086"
TEXT_MUTE    = "#45475a"
SUCCESS      = "#a6e3a1"
SUCCESS_BG   = "#1e3a26"
WARNING      = "#fab387"
WARNING_BG   = "#3a3528"
ERROR        = "#f38ba8"
ERROR_BG     = "#3a2628"
INFO         = "#89b4fa"
INFO_BG      = "#1e3a5a"
BORDER       = "#45475a"
AMBER        = "#f9e2af"

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY   = "'Inter', 'Segoe UI', 'DejaVu Sans', -apple-system, sans-serif"
FONT_SIZE_BASE = "13px"
FONT_SIZE_SM  = "11px"
FONT_SIZE_LG  = "15px"
FONT_SIZE_XL  = "18px"
FONT_SIZE_XXL = "24px"

# ── Spacing ──────────────────────────────────────────────────────────────────
SPACING_XS  = "4px"
SPACING_SM  = "8px"
SPACING_MD  = "12px"
SPACING_LG  = "16px"
SPACING_XL  = "20px"
SPACING_XXL = "24px"

# ── Border Radius ─────────────────────────────────────────────────────────────
RADIUS_SM  = "4px"
RADIUS_MD  = "8px"
RADIUS_LG  = "12px"
RADIUS_XL  = "16px"
RADIUS_FULL = "9999px"

# ── Shadows (simulated with alpha) ────────────────────────────────────────────
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

EMAIL_CATEGORY_COLORS: dict[str, str] = {
    "EXPENSE":       "#a6e3a1",
    "INCOME":        "#f9e2af",
    "INVESTMENT":    "#cba6f7",
    "BILLS":         "#fab387",
    "JOB":           "#89dceb",
    "NEWS":          "#94e2d5",
    "SOCIAL":        "#f38ba8",
    "IMPORTANT":     "#89b4fa",
    "PROMOTIONS":    "#eba0ac",
    "PERSONAL":      "#b4befe",
    "ORDERS":        "#a6e3a1",
    "ACCOUNT":       "#74c7ec",
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


# ── QSS Stylesheet ────────────────────────────────────────────────────────────
MAIN_STYLE = """
QWidget {
    font-family: """ + FONT_FAMILY + """;
    font-size: """ + FONT_SIZE_BASE + """;
    color: """ + TEXT + """;
    background-color: """ + BG + """;
}
QMainWindow, QDialog { background-color: """ + BG + """; }

/* ── Sidebar ── */
#sidebar {
    background-color: """ + SIDEBAR_BG + """;
    border-right: 1px solid """ + BORDER + """;
}
#appTitle { 
    font-size: """ + FONT_SIZE_XL + """; 
    font-weight: bold; 
    color: """ + ACCENT + """; 
    padding: """ + SPACING_SM + """ 0 """ + SPACING_XS + """ 0; 
}
.sectionGroup { 
    margin: """ + SPACING_LG + """ """ + SPACING_MD + """ """ + SPACING_SM + """ """ + SPACING_MD + """;
}
.sectionLabel { 
    color: """ + TEXT_DIM + """; 
    font-size: """ + FONT_SIZE_SM + """; 
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: """ + SPACING_SM + """ 0;
}
#accountPill {
    background-color: """ + SURFACE + """;
    border-radius: """ + RADIUS_FULL + """; 
    padding: """ + SPACING_XS + """ """ + SPACING_MD + """;
    color: """ + TEXT_DIM + """; 
    font-size: """ + FONT_SIZE_SM + """;
}
#accountPill.connected {
    background-color: """ + SUCCESS_BG + """;
    color: """ + SUCCESS + """;
}

/* ── Buttons ── */
QPushButton {
    background-color: """ + SURFACE + """;
    color: """ + TEXT + """;
    border: 1px solid """ + BORDER + """;
    border-radius: """ + RADIUS_MD + """; 
    padding: """ + SPACING_SM + """ """ + SPACING_LG + """;
    min-height: 32px;
}
QPushButton:focus { outline: none; border-color: """ + ACCENT + """; }
QPushButton:hover  { 
    background-color: """ + SURFACE_HOVER + """; 
    border-color: """ + ACCENT + """; 
}
QPushButton:pressed { 
    background-color: """ + SURFACE_ACTIVE + """; 
    border-color: """ + ACCENT_DARK + """;
}
QPushButton:disabled { 
    color: """ + TEXT_DIM + """; 
    border-color: """ + SURFACE + """; 
    background-color: """ + SURFACE + """;
}

#primaryBtn {
    background-color: """ + ACCENT + """;
    color: #ffffff; 
    font-weight: bold; 
    border: none; 
    padding: """ + SPACING_SM + """ """ + SPACING_LG + """;
    min-height: 36px;
}
#primaryBtn:focus { outline: 2px solid """ + ACCENT_LIGHT + """; }
#primaryBtn:hover  { background-color: """ + ACCENT_LIGHT + """; }
#primaryBtn:pressed { background-color: """ + ACCENT_DARK + """; }

#ghostBtn { 
    background: transparent; 
    border: 1px solid """ + ACCENT + """; 
    color: """ + ACCENT + """; 
}
#ghostBtn:focus { outline: none; }
#ghostBtn:hover { background-color: """ + ACCENT + """; color: #ffffff; }

#dangerBtn {
    background-color: """ + ERROR_BG + """;
    color: """ + ERROR + """;
    border: 1px solid """ + ERROR + """;
}
#dangerBtn:focus { outline: none; border-color: """ + ERROR + """; }
#dangerBtn:hover { background-color: """ + ERROR + """; color: #ffffff; }

/* ── Chips ── */
#chipActive {
    background-color: """ + ACCENT + """;
    color: #ffffff; 
    border: none; 
    border-radius: """ + RADIUS_FULL + """; 
    padding: """ + SPACING_XS + """ """ + SPACING_SM + """; 
    font-size: """ + FONT_SIZE_SM + """;
}
#chipInactive {
    background-color: """ + SURFACE + """;
    color: #888888; 
    border: 1px solid """ + BORDER + """;
    border-radius: """ + RADIUS_FULL + """; 
    padding: """ + SPACING_XS + """ """ + SPACING_SM + """; 
    font-size: """ + FONT_SIZE_SM + """;
}
#chipInactive:hover { background-color: """ + SURFACE_HOVER + """; color: """ + TEXT + """; }

/* ── Combo Box ── */
QComboBox {
    background-color: """ + SURFACE + """; 
    border: 1px solid """ + BORDER + """;
    border-radius: """ + RADIUS_SM + """; 
    padding: """ + SPACING_XS + """ """ + SPACING_SM + """; 
    color: """ + TEXT + """;
    min-height: 28px;
}
QComboBox:focus { outline: none; border-color: """ + ACCENT + """; }
QComboBox:hover { border-color: """ + SURFACE_ACTIVE + """; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: """ + SURFACE + """; 
    color: """ + TEXT + """;
    selection-background-color: """ + ACCENT + """;
    border: 1px solid """ + BORDER + """;
    selection-color: #ffffff;
}

/* ── Line Edit & Spin Box ── */
QLineEdit, QSpinBox {
    background-color: """ + SURFACE + """; 
    border: 1px solid """ + BORDER + """;
    border-radius: """ + RADIUS_SM + """; 
    padding: """ + SPACING_XS + """ """ + SPACING_SM + """; 
    color: """ + TEXT + """;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus { 
    outline: none; 
    border-color: """ + ACCENT + """; 
}

/* ── Table ── */
QTableWidget {
    background-color: """ + SURFACE + """;
    alternate-background-color: """ + SURFACE2 + """;
    gridline-color: """ + BORDER + """;
    color: """ + TEXT + """;
    border: 1px solid """ + BORDER + """;
    selection-background-color: """ + ACCENT + """;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: """ + SPACING_SM + """ """ + SPACING_MD + """;
    border-bottom: 1px solid """ + BORDER + """;
}
QTableWidget::item:selected {
    background-color: """ + ACCENT + """;
    color: #ffffff;
}
QTableWidget::item:hover {
    background-color: """ + SURFACE_HOVER + """;
}

/* Row states */
QTableWidget::item[row_excluded="true"] {
    color: """ + TEXT_MUTE + """;
    font-style: italic;
    opacity: 0.6;
}

QTableWidget::item[row_review="true"] {
    background-color: rgba(249, 226, 175, 0.1);
}

QTableWidget::item[field_edited="true"] {
    font-weight: 600;
    color: """ + ACCENT + """;
}

/* Column-specific styling */
QTableWidget::item[column="date"] {
    color: """ + TEXT_DIM + """;
    font-size: """ + FONT_SIZE_SM + """;
}

QTableWidget::item[column="amount"] {
    font-weight: 600;
    color: """ + ACCENT + """;
}

QHeaderView::section {
    background-color: """ + SURFACE_ACTIVE + """;
    color: """ + TEXT + """;
    border: none;
    border-right: 1px solid """ + BORDER + """;
    border-bottom: 2px solid """ + BORDER + """;
    padding: """ + SPACING_SM + """ """ + SPACING_MD + """;
    font-weight: bold;
    font-size: """ + FONT_SIZE_SM + """;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QHeaderView::section:hover { background-color: """ + BORDER + """; }
QHeaderView::section:first {
    border-top-left-radius: """ + RADIUS_SM + """;
}
QHeaderView::section:last {
    border-top-right-radius: """ + RADIUS_SM + """;
}

/* ── Tabs ── */
QTabWidget::pane { 
    border: 1px solid """ + BORDER + """; 
    background-color: """ + BG + """; 
    border-radius: """ + RADIUS_MD + """;
    border-top-left-radius: 0;
    margin-top: -1px;
    padding: """ + SPACING_MD + """;
}
QTabBar::tab {
    background-color: """ + SURFACE + """; 
    color: """ + TEXT_DIM + """;
    border: 1px solid """ + BORDER + """; 
    border-bottom: none;
    padding: """ + SPACING_SM + """ """ + SPACING_LG + """; 
    margin-right: 2px;
    margin-top: 4px;
    border-top-left-radius: """ + RADIUS_SM + """; 
    border-top-right-radius: """ + RADIUS_SM + """; 
    font-weight: 500;
    min-width: 120px;
}
QTabBar::tab:selected { 
    background-color: """ + BG + """; 
    color: """ + ACCENT + """; 
    border-bottom: 2px solid """ + ACCENT + """; 
    font-weight: 600;
}
QTabBar::tab:hover { 
    background-color: """ + SURFACE_HOVER + """; 
    color: """ + TEXT + """; 
}
QTabBar::tab:!selected:hover {
    border-bottom: 1px solid """ + ACCENT + """;
}
QTabBar::tab:focus { 
    outline: 2px solid """ + ACCENT + """; 
    outline-offset: -2px; 
}

/* ── Scrollbars ── */
QScrollBar:vertical { 
    background: """ + SURFACE2 + """; 
    width: 12px; 
    border-radius: """ + RADIUS_SM + """; 
    margin: 0;
}
QScrollBar::handle:vertical { 
    background: """ + SURFACE_ACTIVE + """; 
    border-radius: """ + RADIUS_MD + """; 
    min-height: 30px; 
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background: """ + ACCENT + """; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { 
    background: """ + SURFACE2 + """; 
    height: 12px; 
    border-radius: """ + RADIUS_SM + """;
    margin: 0;
}
QScrollBar::handle:horizontal { 
    background: """ + SURFACE_ACTIVE + """; 
    border-radius: """ + RADIUS_MD + """; 
    min-width: 30px;
    margin: 2px;
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: """ + SURFACE + """; 
    border: 1px solid """ + BORDER + """;
    border-radius: """ + RADIUS_SM + """; 
    height: 8px; 
    text-align: center; 
    font-size: 0px;
}
QProgressBar::chunk { 
    background-color: """ + ACCENT + """; 
    border-radius: """ + RADIUS_SM + """; 
}

/* ── Cards ── */
#summaryCard {
    background-color: """ + SURFACE2 + """; 
    border: 1px solid """ + BORDER + """; 
    border-radius: """ + RADIUS_MD + """; 
}
#summaryValue {
    color: """ + TEXT + """;
    font-size: """ + FONT_SIZE_LG + """;
    font-weight: bold;
}
#cardLabel { 
    color: """ + TEXT_DIM + """; 
    font-size: """ + FONT_SIZE_SM + """; 
    font-weight: 500;
}
#cardValue { 
    color: """ + TEXT + """; 
    font-size: """ + FONT_SIZE_LG + """; 
    font-weight: bold;
    margin-top: """ + SPACING_XS + """;
}

/* ── UI Elements ── */
#separator { 
    background-color: """ + BORDER + """; 
    max-height: 1px; 
    min-height: 1px; 
}
#statusLabel { 
    color: """ + TEXT_DIM + """; 
    font-size: """ + FONT_SIZE_SM + """; 
}
QStatusBar { 
    background-color: """ + SIDEBAR_BG + """; 
    color: """ + TEXT_DIM + """; 
    border-top: 1px solid """ + BORDER + """; 
}
QMessageBox { 
    background-color: """ + SURFACE + """; 
    border-radius: """ + RADIUS_MD + """;
}
QMessageBox QLabel { 
    color: """ + TEXT + """; 
}
#bulkBar { 
    background-color: """ + ACCENT_DARK + """; 
    border-top: 1px solid """ + ACCENT + """; 
}
"""
