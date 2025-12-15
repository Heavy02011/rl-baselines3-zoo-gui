"""Dashboard module with a consolidated control-style layout."""
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.core.process_manager import ProcessManager, ProcessState
from gui.ui.modules.base_module import BaseModule

LOG_LINE_LIMIT = 300  # Maximum blocks to keep in the embedded log
STEERING_SCALE = 100  # Maps [-1, 1] steering to the progress bar range
THROTTLE_SCALE = 100  # Maps [0, 1] throttle to a percentage
COLLECTION_REFRESH_MS = 5000  # Refresh cadence for collection stats (ms)


class DashboardModule(BaseModule):
    """High-level dashboard view inspired by the design mock."""

    MODULE_NAME = "Dashboard"
    MODULE_ICON = "📊"

    def __init__(
        self,
        config_manager,
        process_manager: ProcessManager,
        parent: Optional[QWidget] = None,
    ):
        self._status_labels: dict[str, QLabel] = {}
        self._progress_bars: dict[str, QProgressBar] = {}
        self._steer_bar: Optional[QProgressBar] = None
        self._throttle_bar: Optional[QProgressBar] = None
        self._steer_value: Optional[QLabel] = None
        self._throttle_value: Optional[QLabel] = None
        self._log_view: Optional[QTextEdit] = None
        self._collection_label: Optional[QLabel] = None
        self._refresh_timer: Optional[QTimer] = None
        super().__init__(config_manager, process_manager, parent)

    def _setup_ui(self) -> None:
        """Build dashboard layout."""
        self._main_layout.setContentsMargins(20, 20, 20, 20)
        self._main_layout.setSpacing(14)

        self._main_layout.addLayout(self._build_status_row())
        self._main_layout.addLayout(self._build_control_row())
        self._main_layout.addWidget(self._build_pipeline_card())
        self._main_layout.addWidget(self._build_log_panel())

        # Refresh collection stats periodically
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(COLLECTION_REFRESH_MS)
        self._refresh_timer.timeout.connect(self._refresh_collection_stats)
        self._refresh_collection_stats()

    def _build_status_row(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(12)

        cards = [
            ("simulator", "Simulator", "Unity simulator connection"),
            ("drive", "Manual Drive", "Keyboard/joystick control"),
            ("collect", "Data Collection", "Recording images & telemetry"),
            ("training", "RL Training", "Agent training status"),
        ]

        for col, (key, title, desc) in enumerate(cards):
            card, label = self._status_card(title, desc)
            self._status_labels[key] = label
            grid.addWidget(card, 0, col)

        return grid

    def _status_card(self, title: str, desc: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("DashboardCard")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)
        layout.setContentsMargins(14, 12, 14, 12)

        header = QLabel(title.upper())
        header.setObjectName("CardTitle")
        layout.addWidget(header)

        body = QLabel(desc)
        body.setObjectName("CardSubtitle")
        body.setWordWrap(True)
        layout.addWidget(body)

        status = QLabel("STOPPED")
        status.setObjectName("StatusPill")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status, alignment=Qt.AlignmentFlag.AlignLeft)

        return card, status

    def _build_control_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        row.addWidget(self._build_manual_card(), 2)
        row.addWidget(self._build_telemetry_card(), 1)
        return row

    def _build_manual_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("MANUAL DRIVING")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        # Input selector
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        input_label = QLabel("Input Method")
        input_label.setObjectName("MutedLabel")
        input_row.addWidget(input_label)

        input_row.addStretch()
        self._input_combo = QComboBox()
        self._input_combo.addItem("Keyboard", "keyboard")
        self._input_combo.addItem("Joystick", "joystick")
        current_input = self.config.get("manual_drive.input_method", "keyboard")
        idx = self._input_combo.findData(current_input)
        if idx >= 0:
            self._input_combo.setCurrentIndex(idx)
        self._input_combo.currentIndexChanged.connect(self._persist_input_method)
        input_row.addWidget(self._input_combo)
        layout.addLayout(input_row)

        # Record toggle
        record_row = QHBoxLayout()
        record_row.setSpacing(8)
        record_label = QLabel("Record Data")
        record_label.setObjectName("MutedLabel")
        record_row.addWidget(record_label)
        record_row.addStretch()
        self._record_check = QCheckBox()
        self._record_check.setChecked(
            self.config.get("manual_drive.record_data", False)
        )
        self._record_check.stateChanged.connect(self._persist_record_toggle)
        record_row.addWidget(self._record_check)
        layout.addLayout(record_row)

        # Status badge
        self._drive_status = QLabel("STATUS: IDLE")
        self._drive_status.setObjectName("StatusPill")
        layout.addWidget(self._drive_status, alignment=Qt.AlignmentFlag.AlignLeft)

        return card

    def _build_telemetry_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("LIVE TELEMETRY")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        # Steering
        steer_label = QLabel("Steering")
        steer_label.setObjectName("MutedLabel")
        layout.addWidget(steer_label)

        steer_bar = QProgressBar()
        steer_bar.setRange(-100, 100)
        steer_bar.setValue(0)
        steer_bar.setTextVisible(False)
        layout.addWidget(steer_bar)
        self._steer_bar = steer_bar

        self._steer_value = QLabel("0.00")
        self._steer_value.setObjectName("MetricValue")
        layout.addWidget(self._steer_value, alignment=Qt.AlignmentFlag.AlignRight)

        # Throttle
        throttle_label = QLabel("Throttle")
        throttle_label.setObjectName("MutedLabel")
        layout.addWidget(throttle_label)

        throttle_bar = QProgressBar()
        throttle_bar.setRange(0, 100)
        throttle_bar.setValue(0)
        throttle_bar.setTextVisible(False)
        layout.addWidget(throttle_bar)
        self._throttle_bar = throttle_bar

        self._throttle_value = QLabel("0.00")
        self._throttle_value.setObjectName("MetricValue")
        layout.addWidget(
            self._throttle_value, alignment=Qt.AlignmentFlag.AlignRight
        )

        return card

    def _build_pipeline_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("PIPELINE OVERVIEW")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        layout.addLayout(self._progress_row("Manual Drive", "drive"))
        layout.addLayout(self._progress_row("Data Collection", "collect"))
        layout.addLayout(self._progress_row("RL Training", "training"))
        layout.addLayout(self._collection_row())

        return card

    def _progress_row(self, label_text: str, key: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("MutedLabel")
        row.addWidget(label)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(False)
        self._progress_bars[key] = progress
        row.addWidget(progress)

        return row

    def _collection_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel("Collected Frames")
        label.setObjectName("MutedLabel")
        row.addWidget(label)

        self._collection_label = QLabel("0")
        self._collection_label.setObjectName("MetricValue")
        row.addWidget(self._collection_label, alignment=Qt.AlignmentFlag.AlignRight)

        return row

    def _build_log_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QLabel("CONSOLE LOG")
        header.setObjectName("CardTitle")
        layout.addWidget(header)

        log_view = QTextEdit()
        log_view.setReadOnly(True)
        log_view.setObjectName("DashboardLog")
        layout.addWidget(log_view)
        self._log_view = log_view

        return card

    def set_process_state(self, name: str, state: ProcessState) -> None:
        """Update process state display."""
        label = self._status_labels.get(name)
        text = state.value.upper()
        color = "#22d3ee" if state == ProcessState.RUNNING else "#778599"
        bg = "#123142" if state == ProcessState.RUNNING else "#1f2b3a"

        if label:
            label.setText(text)
            label.setStyleSheet(
                f"padding:4px 10px; border-radius: 10px; background: {bg}; color: {color};"
            )

        if name == "drive" and hasattr(self, "_drive_status"):
            self._drive_status.setText(f"STATUS: {text}")
            self._drive_status.setStyleSheet(
                f"padding:4px 10px; border-radius: 10px; background: {bg}; color: {color};"
            )

        bar = self._progress_bars.get(name)
        if bar:
            bar.setValue(100 if state == ProcessState.RUNNING else 0)

    def append_log(self, text: str) -> None:
        """Append log text to dashboard view."""
        if not self._log_view:
            return
        self._log_view.append(text)

        # Trim excess lines to keep widget light
        doc = self._log_view.document()
        if doc.blockCount() > LOG_LINE_LIMIT:
            # Keep only the most recent LOG_LINE_LIMIT blocks while guarding against negatives
            cursor = self._log_view.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(
                cursor.MoveOperation.Down,
                cursor.MoveMode.KeepAnchor,
                max(0, doc.blockCount() - LOG_LINE_LIMIT),
            )
            cursor.removeSelectedText()

    def update_telemetry(self, steering: float, throttle: float) -> None:
        """Update live telemetry bars."""
        if self._steer_bar:
            self._steer_bar.setValue(
                int(max(-1.0, min(1.0, steering)) * STEERING_SCALE)
            )
        if self._steer_value:
            self._steer_value.setText(f"{steering:.2f}")

        if self._throttle_bar:
            pct = int(max(0.0, min(1.0, throttle)) * THROTTLE_SCALE)
            self._throttle_bar.setValue(pct)
        if self._throttle_value:
            self._throttle_value.setText(f"{throttle:.2f}")

    def _refresh_collection_stats(self) -> None:
        """Pull basic collection stats from configured directory."""
        if not self._collection_label:
            return

        output_dir = self.config.get("data_collection.output_dir", "./collected_data/")
        if not os.path.isabs(output_dir):
            # Derive project root from the known config file location (gui/config.yaml)
            config_path = Path(self.config.config_path).resolve()
            root = config_path.parent.parent
            output_dir = str(root / output_dir)

        images_dir = os.path.join(output_dir, "images")
        count = 0
        if os.path.exists(images_dir):
            count = sum(
                1
                for name in os.listdir(images_dir)
                if name.lower().endswith((".jpg", ".jpeg", ".png"))
            )

        self._collection_label.setText(f"{count} images")

        bar = self._progress_bars.get("collect")
        if bar:
            bar.setValue(100 if count > 0 else 0)

    def _persist_input_method(self) -> None:
        """Persist chosen input method."""
        value = self._input_combo.currentData()
        if value is None:
            return
        self.config.set("manual_drive.input_method", value)
        self.config.save()

    def _persist_record_toggle(self) -> None:
        """Persist record toggle."""
        self.config.set(
            "manual_drive.record_data", self._record_check.isChecked()
        )
        self.config.save()

    def on_show(self) -> None:
        """Start lightweight refreshes when shown."""
        self._refresh_timer.start()
        self._refresh_collection_stats()

    def on_hide(self) -> None:
        """Pause refresh when hidden."""
        self._refresh_timer.stop()
