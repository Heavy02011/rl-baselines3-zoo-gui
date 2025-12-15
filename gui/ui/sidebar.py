"""Navigation sidebar for the main window."""
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class StatusIndicator(QWidget):
    """A status LED indicator with label."""

    def __init__(self, label: str, parent: Optional[QWidget] = None):
        """Initialize the status indicator.

        Args:
            label: Label text for the indicator.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._label = label
        self._active = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(2)

        # Create the indicator dot
        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #666666; font-size: 12px;")

        # Create the label
        self._label_widget = QLabel(self._label)
        self._label_widget.setStyleSheet("font-size: 10px; color: #888888;")

        layout.addWidget(self._dot)
        layout.addWidget(self._label_widget)

    def set_active(self, active: bool) -> None:
        """Set the indicator state.

        Args:
            active: True for green (active), False for gray (inactive).
        """
        self._active = active
        color = "#00ff00" if active else "#666666"
        self._dot.setStyleSheet(f"color: {color}; font-size: 12px;")

    def set_error(self) -> None:
        """Set the indicator to error state (red)."""
        self._dot.setStyleSheet("color: #ff0000; font-size: 12px;")


class SidebarButton(QPushButton):
    """A styled button for the sidebar navigation."""

    def __init__(self, icon: str, text: str, parent: Optional[QWidget] = None):
        """Initialize the sidebar button.

        Args:
            icon: Emoji icon for the button.
            text: Button text.
            parent: Parent widget.
        """
        super().__init__(f"{icon} {text}", parent)
        self.setCheckable(True)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 14px;
                border: none;
                border-radius: 8px;
                background-color: transparent;
                font-size: 13px;
                color: #e5eefb;
            }
            QPushButton:hover {
                background-color: rgba(34, 211, 238, 0.12);
            }
            QPushButton:checked {
                background-color: rgba(34, 211, 238, 0.22);
                border-left: 3px solid #22d3ee;
                color: #ffffff;
            }
        """)


class Sidebar(QFrame):
    """Navigation sidebar with module buttons and status indicators."""

    module_selected = pyqtSignal(str)  # Emits module name

    MODULES = [
        ("📊", "Dashboard", "dashboard"),
        ("🎮", "Simulator", "simulator"),
        ("🚗", "Drive", "drive"),
        ("📸", "Collect", "collect"),
        ("🧠", "Autoencoder", "autoencoder"),
        ("🏋️", "Training", "training"),
        ("▶️", "Run Agent", "enjoy"),
        ("🏆", "Highscores", "highscores"),
        ("📊", "Monitor", "monitor"),
        ("⚙️", "Config", "config"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the sidebar.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._buttons: dict[str, SidebarButton] = {}
        self._indicators: dict[str, StatusIndicator] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(150)
        self.setMaximumWidth(180)
        self.setStyleSheet(
            "background-color: #0d1620; border-right: 1px solid #15202c;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(5)

        # Header with Title and Status LED
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(5)

        title = QLabel("RL Racing")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e5eefb;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Status LED (Summary)
        self._status_led = QLabel("●")
        self._status_led.setStyleSheet("color: #666666; font-size: 16px;")
        self._status_led.setToolTip("System Status")
        header_layout.addWidget(self._status_led)

        layout.addWidget(header_widget)

        # Module buttons
        for icon, text, module_id in self.MODULES:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(
                lambda checked, mid=module_id: self._on_button_clicked(mid)
            )
            self._buttons[module_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Keep track of individual statuses internally if needed, or just map 'simulator' to the main LED
        self._indicators = {}  # We might not need the old indicators widget anymore if we just have one LED

    def _on_button_clicked(self, module_id: str) -> None:
        """Handle button click.

        Args:
            module_id: ID of the clicked module.
        """
        # Uncheck all other buttons
        for mid, btn in self._buttons.items():
            btn.setChecked(mid == module_id)

        self.module_selected.emit(module_id)

    def select_module(self, module_id: str) -> None:
        """Programmatically select a module.

        Args:
            module_id: ID of the module to select.
        """
        if module_id in self._buttons:
            self._on_button_clicked(module_id)

    def set_status(self, indicator_name: str, active: bool) -> None:
        """Set a status indicator state.

        Args:
            indicator_name: Name of the indicator.
            active: True for active (green), False for inactive (gray).
        """
        # For now, we primarily show simulator status on the main LED
        if indicator_name == "simulator":
            color = "#00ff00" if active else "#666666"
            self._status_led.setStyleSheet(f"color: {color}; font-size: 16px;")

    def set_status_error(self, indicator_name: str) -> None:
        """Set a status indicator to error state.

        Args:
            indicator_name: Name of the indicator.
        """
        if indicator_name == "simulator":
            self._status_led.setStyleSheet("color: #ff0000; font-size: 16px;")
