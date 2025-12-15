"""Training monitor module."""
import os
import subprocess
import sys
import webbrowser
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule

# Optional matplotlib import for charts
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class MonitorModule(BaseModule):
    """Module for monitoring training progress."""

    MODULE_NAME = "Training Monitor"
    MODULE_ICON = "📊"

    def _setup_ui(self) -> None:
        """Set up the monitor UI."""
        # Main layout
        # Use a scroll area if needed, but for now simple VBox
        
        # Summary Section
        summary_group = QWidget()
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(0, 0, 0, 10)
        
        self._run_name_label = QLabel("No active run")
        self._run_name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        summary_layout.addWidget(QLabel("Current Run:"))
        summary_layout.addWidget(self._run_name_label)
        
        self.add_widget(summary_group)

        # Metrics Grid
        metrics_widget = QWidget()
        metrics_layout = QHBoxLayout(metrics_widget)
        metrics_layout.setContentsMargins(0, 0, 0, 10)
        
        # Episode
        ep_widget = QWidget()
        ep_layout = QVBoxLayout(ep_widget)
        ep_label_title = QLabel("Episodes")
        ep_label_title.setStyleSheet("color: #888888; font-size: 12px;")
        self._episode_label = QLabel("0")
        self._episode_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        ep_layout.addWidget(ep_label_title)
        ep_layout.addWidget(self._episode_label)
        metrics_layout.addWidget(ep_widget)
        
        # Mean Reward
        rew_widget = QWidget()
        rew_layout = QVBoxLayout(rew_widget)
        rew_label_title = QLabel("Mean Reward")
        rew_label_title.setStyleSheet("color: #888888; font-size: 12px;")
        self._reward_label = QLabel("None")
        self._reward_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4;")
        rew_layout.addWidget(rew_label_title)
        rew_layout.addWidget(self._reward_label)
        metrics_layout.addWidget(rew_widget)
        
        # Mean Length
        len_widget = QWidget()
        len_layout = QVBoxLayout(len_widget)
        len_label_title = QLabel("Mean Length")
        len_label_title.setStyleSheet("color: #888888; font-size: 12px;")
        self._ep_length_label = QLabel("0")
        self._ep_length_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        len_layout.addWidget(len_label_title)
        len_layout.addWidget(self._ep_length_label)
        metrics_layout.addWidget(len_widget)
        
        self.add_widget(metrics_widget)

        # Chart placeholder
        if HAS_MATPLOTLIB:
            self._setup_chart()
        else:
            chart_label = QLabel(
                "📈 Install matplotlib for live reward charts"
            )
            chart_label.setStyleSheet(
                "color: #888888; padding: 20px; background-color: #1e1e1e; "
                "border: 1px solid #333333;"
            )
            self.add_widget(chart_label)

        # Checkpoints table
        self.add_widget(QLabel("Saved Checkpoints:"))
        self._checkpoint_table = QTableWidget()
        self._checkpoint_table.setColumnCount(3)
        self._checkpoint_table.setHorizontalHeaderLabels(
            ["Filename", "Steps", "Date"]
        )
        self._checkpoint_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._checkpoint_table.setMaximumHeight(150)
        self.add_widget(self._checkpoint_table)

        # Buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        refresh_btn = QPushButton("🔄 Refresh Checkpoints")
        refresh_btn.clicked.connect(self._refresh_checkpoints)
        btn_layout.addWidget(refresh_btn)

        self.add_widget(btn_widget)

        # External tools buttons
        tools_widget = QWidget()
        tools_layout = QHBoxLayout(tools_widget)
        tools_layout.setContentsMargins(0, 0, 0, 0)

        tb_btn = QPushButton("📊 Open TensorBoard")
        tb_btn.clicked.connect(self._open_tensorboard)
        tools_layout.addWidget(tb_btn)

        wandb_btn = QPushButton("🌐 Open W&&B Dashboard")
        wandb_btn.clicked.connect(self._open_wandb)
        tools_layout.addWidget(wandb_btn)

        self.add_widget(tools_widget)

        # Models folder selector
        models_widget = QWidget()
        models_layout = QHBoxLayout(models_widget)
        models_layout.setContentsMargins(0, 10, 0, 0)

        self._models_folder = QLabel(
            self.config.get("paths.models_dir", "./logs/")
        )
        models_layout.addWidget(QLabel("Models Folder:"))
        models_layout.addWidget(self._models_folder)
        models_layout.addStretch()

        browse_btn = QPushButton("Change...")
        browse_btn.clicked.connect(self._browse_models_folder)
        models_layout.addWidget(browse_btn)

        self.add_widget(models_widget)

        self.add_stretch()

        # Setup refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_metrics)
        self._refresh_timer.start(5000)  # Refresh every 5 seconds

    def _setup_chart(self) -> None:
        """Set up the matplotlib chart."""
        self._figure = Figure(figsize=(5, 3), dpi=100)
        self._figure.patch.set_facecolor("#1e1e1e")
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor("#1e1e1e")
        self._ax.tick_params(colors="#888888")
        self._ax.spines["bottom"].set_color("#333333")
        self._ax.spines["top"].set_color("#333333")
        self._ax.spines["left"].set_color("#333333")
        self._ax.spines["right"].set_color("#333333")
        self._ax.set_xlabel("Episode", color="#888888")
        self._ax.set_ylabel("Reward", color="#888888")
        self._ax.set_title("Episode Rewards", color="#d4d4d4")

        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(200)
        self.add_widget(self._canvas)

        # Initialize data
        self._reward_history = []
        
    def _connect_signals(self) -> None:
        """Connect signals."""
        process = self.processes.create_process("tensorboard")
        process.output_received.connect(self.log)

    def on_show(self) -> None:
        """Called when module is shown."""
        self._refresh_checkpoints()

    def _refresh_checkpoints(self) -> None:
        """Refresh the checkpoints table."""
        models_dir = self.config.get("paths.models_dir", "./logs/")

        if not os.path.exists(models_dir):
            return

        self._checkpoint_table.setRowCount(0)

        # Find all .zip files (checkpoints)
        checkpoints = []
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file.endswith(".zip"):
                    filepath = os.path.join(root, file)
                    stat = os.stat(filepath)
                    # Try to extract step count from filename
                    steps = "-"
                    if "_steps" in file:
                        try:
                            parts = file.split("_")
                            for i, part in enumerate(parts):
                                if part == "steps" and i > 0:
                                    steps = parts[i - 1]
                                    break
                        except (IndexError, ValueError):
                            pass

                    checkpoints.append(
                        (
                            file,
                            steps,
                            stat.st_mtime,
                        )
                    )

        # Sort by modification time (newest first)
        checkpoints.sort(key=lambda x: x[2], reverse=True)

        # Add to table (limit to 10 most recent)
        for filename, steps, mtime in checkpoints[:10]:
            row = self._checkpoint_table.rowCount()
            self._checkpoint_table.insertRow(row)
            self._checkpoint_table.setItem(
                row, 0, QTableWidgetItem(filename)
            )
            self._checkpoint_table.setItem(row, 1, QTableWidgetItem(steps))
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime(
                "%Y-%m-%d %H:%M"
            )
            self._checkpoint_table.setItem(row, 2, QTableWidgetItem(date_str))

    def _refresh_metrics(self) -> None:
        """Refresh training metrics from logs."""
        # This would parse tensorboard logs or other metrics
        # For now, just update if training is running
        pass

    def set_run_name(self, name: str) -> None:
        """Set the current run name."""
        self._run_name_label.setText(name)
        
    def update_metrics(
        self, episodes: int, mean_reward: float, ep_length: float
    ) -> None:
        """Update displayed metrics.

        Args:
            episodes: Number of episodes.
            mean_reward: Mean episode reward.
            ep_length: Mean episode length.
        """
        self._episode_label.setText(str(episodes))
        self._reward_label.setText(f"{mean_reward:.2f}")
        self._ep_length_label.setText(f"{ep_length:.1f}")

        # Update chart if available
        if HAS_MATPLOTLIB:
            self._reward_history.append(mean_reward)
            if len(self._reward_history) > 100:
                self._reward_history = self._reward_history[-100:]

            self._ax.clear()
            self._ax.plot(
                self._reward_history, color="#0078d4", linewidth=1.5
            )
            self._ax.set_xlabel("Episode", color="#888888")
            self._ax.set_ylabel("Reward", color="#888888")
            self._ax.set_title("Episode Rewards", color="#d4d4d4")
            self._ax.tick_params(colors="#888888")
            self._canvas.draw()

    def _open_tensorboard(self) -> None:
        """Start TensorBoard and open in browser."""
        tb_log = self.config.get(
            "training.tensorboard_log", "/tmp/stable-baselines/"
        )

        self.log(f"[Monitor] Starting TensorBoard at {tb_log}...")

        process = self.processes.get_process("tensorboard")
        if process and not process.is_running():
            command = [
                sys.executable,
                "-m",
                "tensorboard.main",
                "--logdir",
                tb_log,
                "--port",
                "6006",
            ]
            process.start(command)

            # Open browser after a short delay
            QTimer.singleShot(
                2000, lambda: webbrowser.open("http://localhost:6006")
            )
        else:
            # Just open browser if already running
            webbrowser.open("http://localhost:6006")

    def _open_wandb(self) -> None:
        """Open W&B dashboard in browser."""
        entity = self.config.get("wandb.entity", "parkinglotnerds")
        project = self.config.get("wandb.project", "RL_race16")
        url = f"https://wandb.ai/{entity}/{project}"
        webbrowser.open(url)
        self.log(f"[Monitor] Opening W&B dashboard: {url}")

    def _browse_models_folder(self) -> None:
        """Browse for models folder."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Models Folder"
        )
        if path:
            self._models_folder.setText(path)
            self.config.set("paths.models_dir", path)
            self.config.save()
            self._refresh_checkpoints()
