"""
ui_components.py — Reusable UI components for modern, polished interface.

Provides:
- Empty state widgets with helpful messages
- Loading spinners and skeleton loaders
- Consistent styling and behavior
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QMovie
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

from styles import (
    TEXT, TEXT_DIM, TEXT_MUTE, ACCENT, SURFACE, SURFACE2,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_LG,
)


class EmptyStateWidget(QWidget):
    """
    A polished empty state widget with icon, title, and optional description.
    
    Usage:
        empty = EmptyStateWidget(
            icon="📭",
            title="No expenses found",
            description="Try adjusting filters or fetch from Gmail"
        )
    """

    def __init__(
        self,
        icon: str = "📭",
        title: str = "No data",
        description: str = "",
        action_text: str = "",
        action_callback=None,
        parent=None
    ) -> None:
        super().__init__(parent)
        self._setup_ui(icon, title, description, action_text, action_callback)

    def _setup_ui(
        self,
        icon: str,
        title: str,
        description: str,
        action_text: str,
        action_callback
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL, SPACING_XXL, SPACING_XL, SPACING_XL)
        layout.setSpacing(SPACING_MD)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 64px; opacity: 0.6;")
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {TEXT};
            margin: {SPACING_MD} 0 {SPACING_SM} 0;
        """)
        layout.addWidget(title_label)

        # Description
        if description:
            desc_label = QLabel(description)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                font-size: 13px;
                color: {TEXT_DIM};
                max-width: 400px;
                line-height: 1.5;
            """)
            layout.addWidget(desc_label)

        # Action button
        if action_text and action_callback:
            from PyQt6.QtWidgets import QPushButton
            btn = QPushButton(action_text)
            btn.setObjectName("primaryBtn")
            btn.setMinimumWidth(180)
            btn.clicked.connect(action_callback)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()


class LoadingSpinner(QProgressBar):
    """
    A polished loading spinner/progress indicator.

    Use as indeterminate progress bar with smooth animation.
    """

    def __init__(self, text: str = "Loading…", parent=None) -> None:
        super().__init__(parent)
        self._text_label = QLabel(text)
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Container for centered layout
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Configure progress bar as spinner
        self.setRange(0, 0)  # Indeterminate
        self.setFixedWidth(32)
        self.setFixedHeight(32)
        self.setTextVisible(False)
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {SURFACE};
                border: none;
                border-radius: 16px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT};
                border-radius: 16px;
            }}
        """)

        # Text label
        self._text_label.setStyleSheet(f"""
            font-size: 13px;
            color: {TEXT_DIM};
        """)

        layout.addWidget(self)
        layout.addWidget(self._text_label)

        # Set up main widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(container)

    def set_text(self, text: str) -> None:
        """Update the loading text."""
        self._text_label.setText(text)


class SkeletonLoader(QFrame):
    """
    A skeleton loader for showing placeholder content during loading.

    Creates a shimmer effect to indicate content is being loaded.
    """

    def __init__(self, rows: int = 5, parent=None) -> None:
        super().__init__(parent)
        self._rows = rows
        self._setup_ui()
        self._start_animation()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        for _ in range(self._rows):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACING_MD)

            # Checkbox placeholder
            chk = QFrame()
            chk.setFixedSize(20, 20)
            chk.setStyleSheet(f"background-color: {SURFACE}; border-radius: 4px;")
            row_layout.addWidget(chk)

            # Date placeholder
            date = QFrame()
            date.setFixedSize(100, 32)
            date.setStyleSheet(f"background-color: {SURFACE2}; border-radius: 4px;")
            row_layout.addWidget(date)

            # Sender placeholder
            sender = QFrame()
            sender.setFixedSize(200, 32)
            sender.setStyleSheet(f"background-color: {SURFACE2}; border-radius: 4px;")
            row_layout.addWidget(sender)

            # Subject placeholder (stretches)
            subject = QFrame()
            subject.setFixedHeight(32)
            subject.setStyleSheet(f"background-color: {SURFACE2}; border-radius: 4px;")
            row_layout.addWidget(subject, stretch=1)

            # Amount placeholder
            amount = QFrame()
            amount.setFixedSize(100, 32)
            amount.setStyleSheet(f"background-color: {SURFACE2}; border-radius: 4px;")
            row_layout.addWidget(amount)

            layout.addWidget(row)

        layout.addStretch()

    def _start_animation(self) -> None:
        """Start the shimmer animation."""
        self._opacity = 0.3
        self._direction = 1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def _animate(self) -> None:
        """Animate the shimmer effect."""
        self._opacity += 0.02 * self._direction
        if self._opacity >= 0.6:
            self._direction = -1
        elif self._opacity <= 0.3:
            self._direction = 1

        color = QColor(SURFACE2)
        color.setAlphaF(self._opacity)
        self.setStyleSheet(f"""
            QFrame[placeholder="true"] {{
                background-color: {color.name()};
                border-radius: 4px;
            }}
        """)

    def stop_animation(self) -> None:
        """Stop the shimmer animation."""
        if hasattr(self, '_timer'):
            self._timer.stop()


class InfoBanner(QFrame):
    """
    An informational banner with icon and message.

    Types: info, warning, error, success
    """

    def __init__(
        self,
        message: str,
        banner_type: str = "info",
        parent=None
    ) -> None:
        super().__init__(parent)
        self._setup_ui(message, banner_type)

    def _setup_ui(self, message: str, banner_type: str) -> None:
        # Define type-specific styling
        styles = {
            "info": (INFO, "💡"),
            "warning": (WARNING, "⚠️"),
            "error": (ERROR, "❌"),
            "success": (SUCCESS, "✅"),
        }

        color, icon = styles.get(banner_type, styles["info"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_MD)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 18px;")
        layout.addWidget(icon_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            font-size: 13px;
            color: {TEXT};
            line-height: 1.4;
        """)
        layout.addWidget(msg_label, stretch=1)

        # Banner styling
        bg_colors = {
            "info": INFO_BG,
            "warning": WARNING_BG,
            "error": ERROR_BG,
            "success": SUCCESS_BG,
        }

        self.setStyleSheet(f"""
            InfoBanner {{
                background-color: {bg_colors.get(banner_type, INFO_BG)};
                border: 1px solid {color};
                border-radius: {RADIUS_MD};
            }}
        """)


# ── Helper functions ────────────────────────────────────────────────────────────────

def create_empty_state(
    message: str = "No data available",
    description: str = "",
    icon: str = "📭"
) -> EmptyStateWidget:
    """
    Factory function to create an empty state widget.

    Example:
        empty = create_empty_state(
            message="No expenses this month",
            description="Try fetching from Gmail or select a different month",
            icon="💰"
        )
    """
    return EmptyStateWidget(icon=icon, title=message, description=description)


def create_loading_state(message: str = "Loading…") -> LoadingSpinner:
    """
    Factory function to create a loading spinner.

    Example:
        loader = create_loading_state("Fetching expenses from Gmail…")
    """
    return LoadingSpinner(text=message)


def create_info_banner(message: str, banner_type: str = "info") -> InfoBanner:
    """
    Factory function to create an info banner.

    Example:
        banner = create_info_banner(
            "5 expenses need review",
            banner_type="warning"
        )
    """
    return InfoBanner(message=message, banner_type=banner_type)
