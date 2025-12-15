"""Base module class for all GUI modules."""
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from gui.core.config_manager import ConfigManager
    from gui.core.process_manager import ProcessManager


class BaseModule(QFrame):
    """Base class for all module panels."""

    # Signal emitted when the module wants to log a message
    log_message = pyqtSignal(str)

    # Module metadata (override in subclasses)
    MODULE_NAME = "Base Module"
    MODULE_ICON = "📦"

    def __init__(
        self,
        config_manager: "ConfigManager",
        process_manager: "ProcessManager",
        parent: Optional[QWidget] = None,
    ):
        """Initialize the base module.

        Args:
            config_manager: Configuration manager instance.
            process_manager: Process manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = config_manager
        self.processes = process_manager
        self._setup_base_ui()
        self._setup_ui()
        self._connect_signals()

    def _setup_base_ui(self) -> None:
        """Set up the base UI layout."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)

        self.setFrameStyle(QFrame.Shape.StyledPanel)

        # Outer layout with scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        self._main_layout = QVBoxLayout(content_widget)
        self._main_layout.setContentsMargins(15, 15, 15, 15)
        self._main_layout.setSpacing(10)

        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)

        # Module header
        header = QLabel(f"{self.MODULE_ICON} {self.MODULE_NAME}")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        self._main_layout.addWidget(header)

    def _setup_ui(self) -> None:
        """Set up the module-specific UI. Override in subclasses."""
        pass

    def _connect_signals(self) -> None:
        """Connect signals. Override in subclasses."""
        pass

    def on_show(self) -> None:
        """Called when the module is shown. Override for refresh logic."""
        pass

    def on_hide(self) -> None:
        """Called when the module is hidden. Override for cleanup."""
        pass

    def log(self, message: str) -> None:
        """Emit a log message.

        Args:
            message: Message to log.
        """
        self.log_message.emit(message)

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the main layout.

        Args:
            widget: Widget to add.
        """
        self._main_layout.addWidget(widget)

    def add_stretch(self) -> None:
        """Add a stretch to the main layout."""
        self._main_layout.addStretch()
