"""Log panel for displaying process output."""
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QFrame):
    """Panel for displaying log output from processes."""

    MAX_LINES = 1000  # Maximum number of lines to keep

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the log panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._line_count = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Header with title and buttons
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Log Output")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setMaximumWidth(60)
        clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(clear_btn)

        # Auto-scroll toggle
        self._auto_scroll_btn = QPushButton("Auto-scroll")
        self._auto_scroll_btn.setCheckable(True)
        self._auto_scroll_btn.setChecked(True)
        self._auto_scroll_btn.setMaximumWidth(80)
        header_layout.addWidget(self._auto_scroll_btn)

        layout.addWidget(header)

        # Log text area
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #333333;
            }
        """)
        layout.addWidget(self._log_text)

    @pyqtSlot(str)
    def append_log(self, text: str) -> None:
        """Append text to the log.

        Args:
            text: Text to append.
        """
        # Add the text
        self._log_text.append(text)
        self._line_count += 1

        # Trim if too many lines
        if self._line_count > self.MAX_LINES:
            self._trim_lines()

        # Auto-scroll if enabled
        if self._auto_scroll_btn.isChecked():
            scrollbar = self._log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _trim_lines(self) -> None:
        """Remove oldest lines to stay under MAX_LINES."""
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(
            QTextCursor.MoveOperation.Down,
            QTextCursor.MoveMode.KeepAnchor,
            self._line_count - self.MAX_LINES,
        )
        cursor.removeSelectedText()
        self._line_count = self.MAX_LINES

    def clear(self) -> None:
        """Clear all log content."""
        self._log_text.clear()
        self._line_count = 0

    def append_info(self, text: str) -> None:
        """Append info message with formatting.

        Args:
            text: Info message.
        """
        self.append_log(f'<span style="color: #4fc3f7;">[INFO] {text}</span>')

    def append_error(self, text: str) -> None:
        """Append error message with formatting.

        Args:
            text: Error message.
        """
        self.append_log(f'<span style="color: #ef5350;">[ERROR] {text}</span>')

    def append_success(self, text: str) -> None:
        """Append success message with formatting.

        Args:
            text: Success message.
        """
        self.append_log(
            f'<span style="color: #81c784;">[SUCCESS] {text}</span>'
        )
