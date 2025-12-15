"""Manual driving module."""
import os
import sys
from typing import List, Optional

import gymnasium as gym
import gym_donkeycar
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule


class JoystickConfigDialog(QDialog):
    """Dialog for configuring joystick axes."""

    def __init__(self, parent=None, steering_axis=0, throttle_axis=1):
        super().__init__(parent)
        self.setWindowTitle("Joystick Settings")
        self.setModal(True)
        self.steering_axis = steering_axis
        self.throttle_axis = throttle_axis

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.steer_spin = QSpinBox()
        self.steer_spin.setRange(0, 10)
        self.steer_spin.setValue(steering_axis)
        form.addRow("Steering Axis:", self.steer_spin)

        self.throttle_spin = QSpinBox()
        self.throttle_spin.setRange(0, 10)
        self.throttle_spin.setValue(throttle_axis)
        form.addRow("Throttle Axis:", self.throttle_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return self.steer_spin.value(), self.throttle_spin.value()



class DriveModule(BaseModule):
    """Module for manual driving and testing."""

    MODULE_NAME = "Manual Driving"
    MODULE_ICON = "🚗"

    def _setup_ui(self) -> None:
        """Set up the manual driving UI."""
        # Description
        desc = QLabel(
            "Start a manual driving session to test the environment.\n"
            "Use keyboard controls to drive the car."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        self.add_widget(desc)

        # Settings form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Environment selection
        self._env_combo = QComboBox()
        self._env_combo.addItems(self._get_donkey_envs())
        current_env = self.config.get("environment.env_name", "donkey-mountain-track-v0")
        index = self._env_combo.findText(current_env)
        if index >= 0:
            self._env_combo.setCurrentIndex(index)
        form_layout.addRow("Environment:", self._env_combo)

        # Input method selection
        input_layout = QHBoxLayout()
        self._input_combo = QComboBox()
        self._input_combo.addItem("Keyboard", "keyboard")
        self._input_combo.addItem("Joystick/Gamepad", "joystick")
        
        # Load saved input method
        current_input = self.config.get("manual_drive.input_method", "keyboard")
        index = self._input_combo.findData(current_input)
        if index >= 0:
            self._input_combo.setCurrentIndex(index)
            
        input_layout.addWidget(self._input_combo)

        self._settings_btn = QPushButton("⚙️")
        self._settings_btn.setToolTip("Joystick Settings")
        self._settings_btn.setFixedWidth(30)
        self._settings_btn.clicked.connect(self._open_joystick_settings)
        input_layout.addWidget(self._settings_btn)

        form_layout.addRow("Input Method:", input_layout)

        # Recording option
        self._record_checkbox = QCheckBox()
        self._record_checkbox.setChecked(False)
        form_layout.addRow("Record Data:", self._record_checkbox)

        self.add_widget(form_widget)

        # Current values display
        values_widget = QWidget()
        values_layout = QFormLayout(values_widget)
        values_layout.setContentsMargins(0, 10, 0, 10)

        self._steering_label = QLabel("0.00")
        self._steering_label.setStyleSheet("font-family: monospace;")
        values_layout.addRow("Steering:", self._steering_label)

        self._throttle_label = QLabel("0.00")
        self._throttle_label.setStyleSheet("font-family: monospace;")
        values_layout.addRow("Throttle:", self._throttle_label)

        self._speed_label = QLabel("0.00 m/s")
        self._speed_label.setStyleSheet("font-family: monospace;")
        values_layout.addRow("Speed:", self._speed_label)

        self.add_widget(values_widget)

        # Steering bar
        self.add_widget(QLabel("Steering:"))
        self._steering_bar = QProgressBar()
        self._steering_bar.setRange(-100, 100)
        self._steering_bar.setValue(0)
        self._steering_bar.setTextVisible(False)
        self._steering_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                background-color: #1e1e1e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
            }
        """)
        self.add_widget(self._steering_bar)

        # Control buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self._start_btn = QPushButton("▶ Start Driving")
        self._start_btn.clicked.connect(self._start_driving)
        btn_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.clicked.connect(self._stop_driving)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)

        self.add_widget(btn_widget)

        # Test gym button
        test_btn = QPushButton("🧪 Run Test Gym Script")
        test_btn.clicked.connect(self._run_test_gym)
        self.add_widget(test_btn)

        # Save settings
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        self.add_widget(save_btn)

        self.add_stretch()

    def _connect_signals(self) -> None:
        """Connect process signals."""
        process = self.processes.create_process("drive")
        process.state_changed.connect(self._on_state_changed)
        process.output_received.connect(self.log)

    def _start_driving(self) -> None:
        """Start the manual driving session."""
        self.log("[Drive] Starting manual driving session...")

        # Get paths
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        script_path = os.path.join(repo_root, "scripts", "manual_drive.py")

        if not os.path.exists(script_path):
            self.log(f"[Drive] Error: Script not found: {script_path}")
            return

        process = self.processes.get_process("drive")
        if process:
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_root
            command = [sys.executable, script_path]

            # Add environment argument
            env_name = self._env_combo.currentText()
            command.extend(["--env_name", env_name])

            if self._record_checkbox.isChecked():
                # Use configured output directory
                record_dir = self.config.get("data_collection.output_dir", "./collected_data/")
                
                # Ensure absolute path
                if not os.path.isabs(record_dir):
                    record_dir = os.path.join(repo_root, record_dir)
                
                command.extend(["--record_dir", record_dir])
                self.log(f"[Drive] Recording data to: {record_dir}")

            # Add input method arguments
            input_method = self._input_combo.currentData()
            command.extend(["--input_method", input_method])
            
            if input_method == "joystick":
                steer_axis = self.config.get("manual_drive.steering_axis", 0)
                throttle_axis = self.config.get("manual_drive.throttle_axis", 1)
                joy_index = self.config.get("manual_drive.joystick_index", 0)
                
                command.extend(["--steering_axis", str(steer_axis)])
                command.extend(["--throttle_axis", str(throttle_axis)])
                command.extend(["--joystick_index", str(joy_index)])
                
                self.log(f"[Drive] Joystick config: Index={joy_index}, Steer={steer_axis}, Throttle={throttle_axis}")

            # Add connection arguments
            host = self.config.get("simulator.host", "127.0.0.1")
            port = self.config.get("simulator.port", 9091)
            command.extend(["--host", host, "--port", str(port)])
            self.log(f"[Drive] Connecting to {host}:{port}")

            process.start(command, cwd=repo_root, env=env)

    def _open_joystick_settings(self) -> None:
        """Open the joystick configuration dialog."""
        current_steer = self.config.get("manual_drive.steering_axis", 0)
        current_throttle = self.config.get("manual_drive.throttle_axis", 1)

        dialog = JoystickConfigDialog(self, current_steer, current_throttle)
        if dialog.exec():
            new_steer, new_throttle = dialog.get_values()
            self.config.set("manual_drive.steering_axis", new_steer)
            self.config.set("manual_drive.throttle_axis", new_throttle)
            self.config.save()
            self.log(f"[Drive] Saved joystick settings: Steer={new_steer}, Throttle={new_throttle}")

    def log(self, message: str) -> None:
        """Handle log messages and telemetry.

        Args:
            message: Message to log.
        """
        if message.startswith("TELEMETRY:"):
            try:
                # Parse telemetry: TELEMETRY:steering,throttle,speed
                data = message.split(":")[1].strip().split(",")
                if len(data) == 3:
                    steering = float(data[0])
                    throttle = float(data[1])
                    speed = float(data[2])
                    self.update_values(steering, throttle, speed)
            except (ValueError, IndexError):
                pass
        else:
            super().log(message)

    def _stop_driving(self) -> None:
        """Stop the driving session."""
        process = self.processes.get_process("drive")
        if process:
            process.stop()

    def _run_test_gym(self) -> None:
        """Run the test gym script."""
        self.log("[Drive] Starting test gym script...")
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        script_path = os.path.join(repo_root, "scripts", "rbx_test_gym.py")

        if not os.path.exists(script_path):
            self.log(f"[Drive] Error: Script not found: {script_path}")
            return

        process = self.processes.get_process("drive")
        if process:
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_root
            command = [sys.executable, script_path]
            process.start(command, cwd=repo_root, env=env)

    def _on_state_changed(self, state: ProcessState) -> None:
        """Handle drive process state changes.

        Args:
            state: New process state.
        """
        is_running = state == ProcessState.RUNNING
        self._start_btn.setEnabled(not is_running)
        self._stop_btn.setEnabled(is_running)

    def update_values(
        self, steering: float, throttle: float, speed: float
    ) -> None:
        """Update the displayed values.

        Args:
            steering: Current steering value (-1 to 1).
            throttle: Current throttle value (0 to 1).
            speed: Current speed in m/s.
        """
        self._steering_label.setText(f"{steering:.2f}")
        self._throttle_label.setText(f"{throttle:.2f}")
        self._speed_label.setText(f"{speed:.2f} m/s")
        self._steering_bar.setValue(int(steering * 100))

    def _save_settings(self) -> None:
        """Save current settings."""
        self.config.set("environment.env_name", self._env_combo.currentText())
        self.config.set("manual_drive.input_method", self._input_combo.currentData())
        self.config.save()
        self.log("[Drive] Settings saved")

    def _get_donkey_envs(self) -> List[str]:
        """Get list of available donkeycar environments.

        Returns:
            List of environment IDs.
        """
        # Ensure registration
        import gym_donkeycar.envs.donkey_env  # noqa

        envs = [
            env_id
            for env_id in gym.envs.registry.keys()
            if env_id.startswith("donkey-")
        ]
        return sorted(envs)

