"""
styles.py — Colour tokens and CTk theme configuration.
QSS/QPalette removed; colour constants reused for matplotlib and runtime badge colouring.
"""

import customtkinter as ctk

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
FONT_FAMILY    = "Inter"
FONT_SIZE_BASE = 13
FONT_SIZE_SM   = 11
FONT_SIZE_XS   = 10
FONT_SIZE_LG   = 15
FONT_SIZE_XL   = 18
FONT_SIZE_XXL  = 24

# ── Spacing (pixels) ─────────────────────────────────────────────────────────
SPACING_XS  = 4
SPACING_SM  = 8
SPACING_MD  = 12
SPACING_LG  = 16
SPACING_XL  = 20
SPACING_XXL = 24

# ── Border Radius ─────────────────────────────────────────────────────────────
RADIUS_SM   = 4
RADIUS_MD   = 8
RADIUS_LG   = 12
RADIUS_XL   = 16
RADIUS_FULL = 999

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


# ── CTk Theme Configuration ───────────────────────────────────────────────────
def configure_ctk_theme() -> None:
    """Apply the Catppuccin-Mocha dark palette to CustomTkinter."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    # Override CTk's internal colour map for a fully custom palette
    theme = ctk.ThemeManager.theme
    if not theme:
        return

    def _set(component: str, key: str, light: str, dark: str) -> None:
        try:
            theme[component][key] = [light, dark]
        except (KeyError, TypeError):
            pass

    # CTkFrame
    _set("CTkFrame",       "fg_color",       SURFACE2,  SURFACE2)
    _set("CTkFrame",       "top_fg_color",   SURFACE,   SURFACE)
    _set("CTkFrame",       "border_color",   BORDER,    BORDER)

    # CTkButton
    _set("CTkButton",      "fg_color",       ACCENT,    ACCENT)
    _set("CTkButton",      "hover_color",    ACCENT_LIGHT, ACCENT_LIGHT)
    _set("CTkButton",      "text_color",     "#1e1e2e", "#1e1e2e")
    _set("CTkButton",      "border_color",   ACCENT_DARK, ACCENT_DARK)

    # CTkLabel
    _set("CTkLabel",       "fg_color",       "transparent", "transparent")
    _set("CTkLabel",       "text_color",     TEXT, TEXT)

    # CTkEntry
    _set("CTkEntry",       "fg_color",       SURFACE, SURFACE)
    _set("CTkEntry",       "border_color",   BORDER_BRIGHT, BORDER_BRIGHT)
    _set("CTkEntry",       "text_color",     TEXT, TEXT)
    _set("CTkEntry",       "placeholder_text_color", TEXT_DIM, TEXT_DIM)

    # CTkComboBox
    _set("CTkComboBox",    "fg_color",       SURFACE, SURFACE)
    _set("CTkComboBox",    "border_color",   BORDER_BRIGHT, BORDER_BRIGHT)
    _set("CTkComboBox",    "button_color",   SURFACE_HOVER, SURFACE_HOVER)
    _set("CTkComboBox",    "button_hover_color", SURFACE_ACTIVE, SURFACE_ACTIVE)
    _set("CTkComboBox",    "text_color",     TEXT, TEXT)
    _set("CTkComboBox",    "dropdown_fg_color", SURFACE, SURFACE)
    _set("CTkComboBox",    "dropdown_text_color", TEXT, TEXT)
    _set("CTkComboBox",    "dropdown_hover_color", SURFACE_HOVER, SURFACE_HOVER)

    # CTkScrollableFrame
    _set("CTkScrollableFrame", "fg_color",   SURFACE2, SURFACE2)
    _set("CTkScrollableFrame", "border_color", BORDER, BORDER)
    _set("CTkScrollableFrame", "scrollbar_button_color", BORDER_BRIGHT, BORDER_BRIGHT)
    _set("CTkScrollableFrame", "scrollbar_button_hover_color", ACCENT_DARK, ACCENT_DARK)

    # CTkTabview
    _set("CTkTabview",     "fg_color",       BG,      BG)
    _set("CTkTabview",     "segmented_button_fg_color", SURFACE2, SURFACE2)
    _set("CTkTabview",     "segmented_button_selected_color", BG, BG)
    _set("CTkTabview",     "segmented_button_selected_hover_color", SURFACE_HOVER, SURFACE_HOVER)
    _set("CTkTabview",     "segmented_button_unselected_color", SURFACE2, SURFACE2)
    _set("CTkTabview",     "segmented_button_unselected_hover_color", SURFACE_HOVER, SURFACE_HOVER)
    _set("CTkTabview",     "text_color",     TEXT, TEXT)
    _set("CTkTabview",     "text_color_disabled", TEXT_DIM, TEXT_DIM)
    _set("CTkTabview",     "border_color",   BORDER, BORDER)

    # CTkProgressBar
    _set("CTkProgressBar", "fg_color",       SURFACE, SURFACE)
    _set("CTkProgressBar", "progress_color", ACCENT,  ACCENT)
    _set("CTkProgressBar", "border_color",   BORDER,  BORDER)

    # CTkCheckBox
    _set("CTkCheckBox",    "fg_color",       ACCENT,  ACCENT)
    _set("CTkCheckBox",    "hover_color",    ACCENT_DARK, ACCENT_DARK)
    _set("CTkCheckBox",    "checkmark_color", "#1e1e2e", "#1e1e2e")
    _set("CTkCheckBox",    "border_color",   BORDER_BRIGHT, BORDER_BRIGHT)
    _set("CTkCheckBox",    "text_color",     TEXT, TEXT)

    # CTkSlider
    _set("CTkSlider",      "fg_color",       SURFACE_HOVER, SURFACE_HOVER)
    _set("CTkSlider",      "progress_color", ACCENT, ACCENT)
    _set("CTkSlider",      "button_color",   ACCENT, ACCENT)
    _set("CTkSlider",      "button_hover_color", ACCENT_LIGHT, ACCENT_LIGHT)

    # CTkTextbox
    _set("CTkTextbox",     "fg_color",       SURFACE, SURFACE)
    _set("CTkTextbox",     "border_color",   BORDER_BRIGHT, BORDER_BRIGHT)
    _set("CTkTextbox",     "text_color",     TEXT, TEXT)
    _set("CTkTextbox",     "scrollbar_button_color", BORDER_BRIGHT, BORDER_BRIGHT)
    _set("CTkTextbox",     "scrollbar_button_hover_color", ACCENT_DARK, ACCENT_DARK)

    # CTkSegmentedButton
    _set("CTkSegmentedButton", "fg_color",          SURFACE2, SURFACE2)
    _set("CTkSegmentedButton", "selected_color",    ACCENT, ACCENT)
    _set("CTkSegmentedButton", "selected_hover_color", ACCENT_LIGHT, ACCENT_LIGHT)
    _set("CTkSegmentedButton", "unselected_color",  SURFACE, SURFACE)
    _set("CTkSegmentedButton", "unselected_hover_color", SURFACE_HOVER, SURFACE_HOVER)
    _set("CTkSegmentedButton", "text_color",        TEXT, TEXT)
    _set("CTkSegmentedButton", "text_color_disabled", TEXT_DIM, TEXT_DIM)

def bind_tree_scroll(tree):
    """Enable mouse wheel scrolling on Linux (X11) for ttk.Treeview widgets."""
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))
