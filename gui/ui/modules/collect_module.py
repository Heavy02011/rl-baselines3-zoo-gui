"""Data collection module."""
import os
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule


class CollectModule(BaseModule):
    """Module for data collection."""

    MODULE_NAME = "Data Collection"
    MODULE_ICON = "📸"

    def _setup_ui(self) -> None:
        """Set up the data collection UI."""
        # Description
        desc = QLabel(
            "Collect images from the simulator for training autoencoders.\n"
            "Drive the car while recording to collect diverse data."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        self.add_widget(desc)

        # Output directory
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)

        self._output_dir = QLineEdit()
        self._output_dir.setText(
            self.config.get("data_collection.output_dir", "./collected_data/")
        )
        dir_layout.addWidget(self._output_dir)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(browse_btn)

        self.add_widget(QLabel("Output Directory:"))
        self.add_widget(dir_widget)

        # Settings form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 10, 0, 10)

        # Save format
        self._format_combo = QComboBox()
        self._format_combo.addItem("JPEG", "jpg")
        self._format_combo.addItem("PNG", "png")
        current_format = self.config.get("data_collection.save_format", "jpg")
        index = self._format_combo.findData(current_format)
        if index >= 0:
            self._format_combo.setCurrentIndex(index)
        form_layout.addRow("Image Format:", self._format_combo)

        self.add_widget(form_widget)

        # Statistics
        stats_widget = QWidget()
        stats_layout = QFormLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #0078d4;"
        )
        stats_layout.addRow("Images Collected:", self._count_label)

        self._size_label = QLabel("0 MB")
        stats_layout.addRow("Total Size:", self._size_label)

        self.add_widget(stats_widget)

        # Control buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self._start_btn = QPushButton("▶ Start Collection")
        self._start_btn.clicked.connect(self._start_collection)
        btn_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.clicked.connect(self._stop_collection)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)

        self.add_widget(btn_widget)

        # Additional buttons
        btn_widget2 = QWidget()
        btn_layout2 = QHBoxLayout(btn_widget2)
        btn_layout2.setContentsMargins(0, 0, 0, 0)

        refresh_btn = QPushButton("🔄 Refresh Count")
        refresh_btn.clicked.connect(self._refresh_count)
        btn_layout2.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑 Clear Data")
        clear_btn.clicked.connect(self._clear_data)
        btn_layout2.addWidget(clear_btn)

        self.add_widget(btn_widget2)

        # Save settings
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        self.add_widget(save_btn)

        self.add_stretch()

        # Initial count refresh
        self._refresh_count()

        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_count)
        self._refresh_timer.setInterval(1000)  # 1 second

    def on_show(self) -> None:
        """Called when module is shown."""
        self._refresh_count()
        self._refresh_timer.start()

    def on_hide(self) -> None:
        """Called when module is hidden."""
        self._refresh_timer.stop()

    def _connect_signals(self) -> None:
        """Connect process signals."""
        process = self.processes.create_process("collect")
        process.state_changed.connect(self._on_state_changed)
        process.output_received.connect(self.log)

    def _browse_dir(self) -> None:
        """Browse for output directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if path:
            self._output_dir.setText(path)

    def _start_collection(self) -> None:
        """Start data collection."""
        self.log("[Collect] Starting data collection...")
        # Note: Actual collection would be integrated with the driving module
        # This is a placeholder for the collection process
        self.log("[Collect] Data collection is integrated with driving mode.")
        self.log("[Collect] Enable 'Record Data' in the Drive module and start driving.")

    def _stop_collection(self) -> None:
        """Stop data collection."""
        process = self.processes.get_process("collect")
        if process:
            process.stop()

    def _on_state_changed(self, state: ProcessState) -> None:
        """Handle collection state changes.

        Args:
            state: New process state.
        """
        is_running = state == ProcessState.RUNNING
        self._start_btn.setEnabled(not is_running)
        self._stop_btn.setEnabled(is_running)

    def _refresh_count(self) -> None:
        """Refresh the image count from the output directory."""
        output_dir = self._output_dir.text()
        images_dir = os.path.join(output_dir, "images")

        if not os.path.exists(images_dir):
            self._count_label.setText("0")
            self._size_label.setText("0 MB")
            return

        count = 0
        total_size = 0

        for filename in os.listdir(images_dir):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                count += 1
                filepath = os.path.join(images_dir, filename)
                total_size += os.path.getsize(filepath)

        self._count_label.setText(str(count))
        self._size_label.setText(f"{total_size / (1024 * 1024):.2f} MB")

    def _clear_data(self) -> None:
        """Clear collected data."""
        output_dir = self._output_dir.text()
        images_dir = os.path.join(output_dir, "images")

        if not os.path.exists(images_dir):
            self.log("[Collect] No data to clear")
            return

        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Clear Data",
            f"Are you sure you want to delete all images in:\n{images_dir}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            import shutil

            try:
                shutil.rmtree(images_dir)
                os.makedirs(images_dir, exist_ok=True)
                self._refresh_count()
                self.log("[Collect] Data cleared successfully")
            except Exception as e:
                self.log(f"[Collect] Error clearing data: {e}")

    def _save_settings(self) -> None:
        """Save current settings."""
        self.config.set("data_collection.output_dir", self._output_dir.text())
        self.config.set(
            "data_collection.save_format", self._format_combo.currentData()
        )
        self.config.save()
        self.log("[Collect] Settings saved")
