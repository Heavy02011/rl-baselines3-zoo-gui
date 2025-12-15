"""Simulator control module."""
import os
from typing import Optional

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule


class SimulatorModule(BaseModule):
    """Module for controlling the DonkeyCar simulator."""

    MODULE_NAME = "Simulator Control"
    MODULE_ICON = "🎮"

    TRACKS = [
        ("mountain_track", "Mountain Track"),
        ("warehouse", "Warehouse"),
        ("generated_track", "Generated Track"),
        ("roboracingleague_1", "Roboracing League 1"),
    ]

    def _setup_ui(self) -> None:
        """Set up the simulator control UI."""
        # Executable path section
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)

        self._exe_path = QLineEdit()
        self._exe_path.setPlaceholderText("Path to simulator executable...")
        self._exe_path.setText(self.config.get("simulator.exe_path", ""))
        path_layout.addWidget(self._exe_path)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_exe)
        path_layout.addWidget(browse_btn)

        self.add_widget(QLabel("Simulator Executable:"))
        self.add_widget(path_widget)

        # Settings form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 10, 0, 10)

        # Track selection
        self._track_combo = QComboBox()
        for track_id, track_name in self.TRACKS:
            self._track_combo.addItem(track_name, track_id)
        current_level = self.config.get("simulator.level", "mountain_track")
        index = self._track_combo.findData(current_level)
        if index >= 0:
            self._track_combo.setCurrentIndex(index)
        form_layout.addRow("Track:", self._track_combo)

        # Host
        self._host_input = QLineEdit()
        self._host_input.setText(self.config.get("simulator.host", "localhost"))
        form_layout.addRow("Host:", self._host_input)

        # Port
        self._port_input = QSpinBox()
        self._port_input.setRange(1024, 65535)
        self._port_input.setValue(self.config.get("simulator.port", 9091))
        form_layout.addRow("Port:", self._port_input)

        # Resolution
        res_widget = QWidget()
        res_layout = QHBoxLayout(res_widget)
        res_layout.setContentsMargins(0, 0, 0, 0)

        self._width_input = QSpinBox()
        self._width_input.setRange(320, 3840)
        self._width_input.setValue(self.config.get("simulator.width", 640))
        self._width_input.setSuffix(" px")

        self._height_input = QSpinBox()
        self._height_input.setRange(240, 2160)
        self._height_input.setValue(self.config.get("simulator.height", 480))
        self._height_input.setSuffix(" px")

        res_layout.addWidget(QLabel("W:"))
        res_layout.addWidget(self._width_input)
        res_layout.addWidget(QLabel("H:"))
        res_layout.addWidget(self._height_input)

        form_layout.addRow("Resolution:", res_widget)

        # Fullscreen
        self._fullscreen_check = QCheckBox()
        self._fullscreen_check.setChecked(
            self.config.get("simulator.fullscreen", False)
        )
        form_layout.addRow("Fullscreen:", self._fullscreen_check)

        # Time Scale
        self._time_scale_input = QDoubleSpinBox()
        self._time_scale_input.setRange(0.1, 20.0)
        self._time_scale_input.setSingleStep(0.1)
        self._time_scale_input.setValue(
            self.config.get("simulator.time_scale", 4.0)
        )
        form_layout.addRow("Time Scale:", self._time_scale_input)

        self.add_widget(form_widget)

        # Status indicator
        self._status_label = QLabel("Status: Not Running")
        self._status_label.setStyleSheet("color: #888888;")
        self.add_widget(self._status_label)

        # Control buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self._start_btn = QPushButton("▶ Start Simulator")
        self._start_btn.clicked.connect(self._start_simulator)
        btn_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⏹ Stop Simulator")
        self._stop_btn.clicked.connect(self._stop_simulator)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)

        self.add_widget(btn_widget)

        # Save settings button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        self.add_widget(save_btn)

        self.add_stretch()

    def _connect_signals(self) -> None:
        """Connect process signals."""
        process = self.processes.create_process("simulator")
        process.state_changed.connect(self._on_state_changed)
        process.output_received.connect(self.log)

    def _browse_exe(self) -> None:
        """Open file browser for simulator executable."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Simulator Executable",
            "",
            "Executables (*.x86_64 *.exe *);;All Files (*)",
        )
        if path:
            self._exe_path.setText(path)

    def _start_simulator(self) -> None:
        """Start the simulator."""
        exe_path = self._exe_path.text()
        if not exe_path or not os.path.exists(exe_path):
            self.log("[Simulator] Error: Invalid executable path")
            return

        port = self._port_input.value()
        track = self._track_combo.currentData()
        time_scale = self._time_scale_input.value()

        process = self.processes.get_process("simulator")
        if process:
            # Build command - DonkeyCar simulator uses command line args
            command = [
                exe_path,
                "--port",
                str(port),
                "--track",
                track,
                "--time_scale",
                str(time_scale),
                "-screen-width",
                str(self._width_input.value()),
                "-screen-height",
                str(self._height_input.value()),
                "-screen-fullscreen",
                "1" if self._fullscreen_check.isChecked() else "0",
            ]
            process.start(command, cwd=os.path.dirname(exe_path))

    def _stop_simulator(self) -> None:
        """Stop the simulator."""
        process = self.processes.get_process("simulator")
        if process:
            process.stop()

    def _on_state_changed(self, state: ProcessState) -> None:
        """Handle simulator state changes.

        Args:
            state: New process state.
        """
        is_running = state == ProcessState.RUNNING
        self._start_btn.setEnabled(not is_running)
        self._stop_btn.setEnabled(is_running)

        if state == ProcessState.RUNNING:
            self._status_label.setText("Status: Running ✓")
            self._status_label.setStyleSheet("color: #00ff00;")
        elif state == ProcessState.ERROR:
            self._status_label.setText("Status: Error ✗")
            self._status_label.setStyleSheet("color: #ff0000;")
        else:
            self._status_label.setText("Status: Not Running")
            self._status_label.setStyleSheet("color: #888888;")

    def _save_settings(self) -> None:
        """Save current settings to config."""
        self.config.set("simulator.exe_path", self._exe_path.text())
        self.config.set("simulator.host", self._host_input.text())
        self.config.set("simulator.port", self._port_input.value())
        self.config.set("simulator.level", self._track_combo.currentData())
        self.config.set("simulator.width", self._width_input.value())
        self.config.set("simulator.height", self._height_input.value())
        self.config.set("simulator.fullscreen", self._fullscreen_check.isChecked())
        self.config.set("simulator.time_scale", self._time_scale_input.value())
        self.config.save()
        self.log("[Simulator] Settings saved")
