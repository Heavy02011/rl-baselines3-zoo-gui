"""RL Training module."""
import os
import sys
from typing import List, Optional, Tuple

import gymnasium as gym
import gym_donkeycar
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QWidget,
)

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule


class TrainingModule(BaseModule):
    """Module for RL training control."""

    MODULE_NAME = "RL Training"
    MODULE_ICON = "🏋️"

    ALGORITHMS = [
        ("tqc", "TQC (Truncated Quantile Critics)"),
        ("sac", "SAC (Soft Actor-Critic)"),
        ("ppo", "PPO (Proximal Policy Optimization)"),
        ("td3", "TD3 (Twin Delayed DDPG)"),
    ]

    def _setup_ui(self) -> None:
        """Set up the training UI."""
        # Description
        desc = QLabel(
            "Configure and start reinforcement learning training.\n"
            "Monitor progress and manage checkpoints."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        self.add_widget(desc)

        # Environment selection
        env_widget = QWidget()
        env_layout = QFormLayout(env_widget)
        env_layout.setContentsMargins(0, 0, 0, 0)

        self._env_combo = QComboBox()
        self._env_combo.addItems(self._get_donkey_envs())
        current_env = self.config.get("environment.env_name", "donkey-mountain-track-v0")
        index = self._env_combo.findText(current_env)
        if index >= 0:
            self._env_combo.setCurrentIndex(index)
        env_layout.addRow("Environment:", self._env_combo)

        # Steering limits
        self._steer_left_input = QDoubleSpinBox()
        self._steer_left_input.setRange(-1.0, 0.0)
        self._steer_left_input.setSingleStep(0.1)
        self._steer_left_input.setValue(
            self.config.get("environment.steer_left", -1.0)
        )
        env_layout.addRow("Steer Left:", self._steer_left_input)

        self._steer_right_input = QDoubleSpinBox()
        self._steer_right_input.setRange(0.0, 1.0)
        self._steer_right_input.setSingleStep(0.1)
        self._steer_right_input.setValue(
            self.config.get("environment.steer_right", 1.0)
        )
        env_layout.addRow("Steer Right:", self._steer_right_input)

        # Throttle limits
        self._throttle_min_input = QDoubleSpinBox()
        self._throttle_min_input.setRange(-1.0, 1.0)
        self._throttle_min_input.setSingleStep(0.1)
        self._throttle_min_input.setValue(
            self.config.get("environment.throttle_min", 0.0)
        )
        env_layout.addRow("Throttle Min:", self._throttle_min_input)

        self._throttle_max_input = QDoubleSpinBox()
        self._throttle_max_input.setRange(0.0, 1.0)
        self._throttle_max_input.setSingleStep(0.1)
        self._throttle_max_input.setValue(
            self.config.get("environment.throttle_max", 1.0)
        )
        env_layout.addRow("Throttle Max:", self._throttle_max_input)
        
        self.add_widget(env_widget)

        # Algorithm selection
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Algorithm
        self._algo_combo = QComboBox()
        for algo_id, algo_name in self.ALGORITHMS:
            self._algo_combo.addItem(algo_name, algo_id)
        current_algo = self.config.get("training.algorithm", "tqc")
        index = self._algo_combo.findData(current_algo)
        if index >= 0:
            self._algo_combo.setCurrentIndex(index)
        form_layout.addRow("Algorithm:", self._algo_combo)

        # Total timesteps
        self._timesteps_input = QSpinBox()
        self._timesteps_input.setRange(1000, 100000000)
        self._timesteps_input.setSingleStep(100000)
        self._timesteps_input.setValue(
            self.config.get("training.total_timesteps", 2000000)
        )
        form_layout.addRow("Total Timesteps:", self._timesteps_input)

        # Save frequency
        self._save_freq_input = QSpinBox()
        self._save_freq_input.setRange(-1, 1000000)
        self._save_freq_input.setSingleStep(5000)
        self._save_freq_input.setValue(
            self.config.get("training.save_freq", 20000)
        )
        form_layout.addRow("Save Frequency:", self._save_freq_input)

        # Eval frequency
        self._eval_freq_input = QSpinBox()
        self._eval_freq_input.setRange(-1, 1000000)
        self._eval_freq_input.setSingleStep(5000)
        self._eval_freq_input.setValue(
            self.config.get("training.eval_freq", -1)
        )
        form_layout.addRow("Eval Frequency (-1=off):", self._eval_freq_input)

        self.add_widget(form_widget)

        # Hyperparams file
        self.add_widget(QLabel("Hyperparameters File:"))
        hyperparams_widget = QWidget()
        hyperparams_layout = QHBoxLayout(hyperparams_widget)
        hyperparams_layout.setContentsMargins(0, 0, 0, 0)

        self._hyperparams_path = QLineEdit()
        self._hyperparams_path.setText(
            self.config.get("training.hyperparams_file", "./hyperparams/tqc.yml")
        )
        hyperparams_layout.addWidget(self._hyperparams_path)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_hyperparams)
        hyperparams_layout.addWidget(browse_btn)

        self.add_widget(hyperparams_widget)

        # Checkpoint to continue from
        self.add_widget(QLabel("Continue from Checkpoint (optional):"))
        checkpoint_widget = QWidget()
        checkpoint_layout = QHBoxLayout(checkpoint_widget)
        checkpoint_layout.setContentsMargins(0, 0, 0, 0)

        self._checkpoint_path = QLineEdit()
        self._checkpoint_path.setPlaceholderText("Leave empty to start fresh...")
        checkpoint_layout.addWidget(self._checkpoint_path)

        checkpoint_btn = QPushButton("Browse...")
        checkpoint_btn.clicked.connect(self._browse_checkpoint)
        checkpoint_layout.addWidget(checkpoint_btn)

        self.add_widget(checkpoint_widget)

        # Options
        options_widget = QWidget()
        options_layout = QFormLayout(options_widget)
        options_layout.setContentsMargins(0, 10, 0, 10)

        # W&B logging
        self._wandb_checkbox = QCheckBox()
        self._wandb_checkbox.setChecked(
            self.config.get("wandb.enabled", False)
        )
        options_layout.addRow("Enable W&&B Logging:", self._wandb_checkbox)

        # Save replay buffer
        self._replay_checkbox = QCheckBox()
        self._replay_checkbox.setChecked(
            self.config.get("training.save_replay_buffer", True)
        )
        options_layout.addRow("Save Replay Buffer:", self._replay_checkbox)

        self.add_widget(options_widget)

        # Progress section
        self.add_widget(QLabel("Training Progress:"))
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self.add_widget(self._progress_bar)

        self._progress_label = QLabel("Steps: 0 / 0 | Episodes: 0")
        self._progress_label.setStyleSheet("color: #888888;")
        self.add_widget(self._progress_label)

        # Control buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self._start_btn = QPushButton("▶ Start Training")
        self._start_btn.clicked.connect(self._start_training)
        self._start_btn.setStyleSheet(
            "background-color: #107c10; color: white; font-weight: bold;"
        )
        btn_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.clicked.connect(self._stop_training)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "background-color: #d13438; color: white;"
        )
        btn_layout.addWidget(self._stop_btn)

        self.add_widget(btn_widget)

        # Save settings
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        self.add_widget(save_btn)

        self.add_stretch()

    def _connect_signals(self) -> None:
        """Connect process signals."""
        process = self.processes.create_process("training")
        process.state_changed.connect(self._on_state_changed)
        process.output_received.connect(self._parse_output)

    def _browse_hyperparams(self) -> None:
        """Browse for hyperparameters file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Hyperparameters File",
            "",
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )
        if path:
            self._hyperparams_path.setText(path)

    def _browse_checkpoint(self) -> None:
        """Browse for checkpoint file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Checkpoint File",
            "",
            "ZIP Files (*.zip);;All Files (*)",
        )
        if path:
            self._checkpoint_path.setText(path)

    def _predict_next_run_id(self, repo_root: str, algo: str, env_name: str) -> str:
        """Predict the next run folder name used by rl_zoo3."""
        log_path = os.path.join(repo_root, "logs", algo)
        if not os.path.exists(log_path):
             return f"{env_name}_1"
        
        max_id = 0
        for name in os.listdir(log_path):
            if name.startswith(env_name) and "_" in name:
                try:
                     # name is env_name_N
                     # split by last underscore
                     parts = name.split("_")
                     if parts[-1].isdigit():
                         max_id = max(max_id, int(parts[-1]))
                except:
                     pass
        
        return f"{env_name}_{max_id + 1}"

    def _start_training(self) -> None:
        """Start RL training."""
        self.log("[Training] Starting RL training...")

        # Get paths
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        train_script = os.path.join(repo_root, "scripts", "train.py")



        # Build command
        algo = self._algo_combo.currentData()
        env_name = self._env_combo.currentText()
        timesteps = self._timesteps_input.value()
        save_freq = self._save_freq_input.value()
        eval_freq = self._eval_freq_input.value()
        tb_log = self.config.get("training.tensorboard_log", "/tmp/stable-baselines/")

        if os.path.exists(train_script):
             command = [
                sys.executable,
                train_script,
                "--algo",
                algo,
                "--env",
                env_name,
                "-n",
                str(timesteps),
                "--save-freq",
                str(save_freq),
                "--eval-freq",
                str(eval_freq),
                "--tensorboard-log",
                tb_log,
                "--env-kwargs",
                f"steer_left:{self._steer_left_input.value()}",
                f"steer_right:{self._steer_right_input.value()}",
                f"throttle_min:{self._throttle_min_input.value()}",
                f"throttle_max:{self._throttle_max_input.value()}",
            ]
        else:
             # Fallback to module execution
             self.log(f"[Training] Script not found at {train_script}, using python -m rl_zoo3.train")
             command = [
                sys.executable,
                "-m",
                "rl_zoo3.train",
                "--algo",
                algo,
                "--env",
                env_name,
                "-n",
                str(timesteps),
                "--save-freq",
                str(save_freq),
                "--eval-freq",
                str(eval_freq),
                "--tensorboard-log",
                tb_log,
                "--env-kwargs",
                f"steer_left:{self._steer_left_input.value()}",
                f"steer_right:{self._steer_right_input.value()}",
                f"throttle_min:{self._throttle_min_input.value()}",
                f"throttle_max:{self._throttle_max_input.value()}",
            ]

        # Add checkpoint if specified
        checkpoint = self._checkpoint_path.text()
        if checkpoint and os.path.exists(checkpoint):
            command.extend(["-i", checkpoint])

        # Add replay buffer option
        if self._replay_checkbox.isChecked():
            command.append("--save-replay-buffer")

        # Add W&B options
        if self._wandb_checkbox.isChecked():
            command.append("--track")
            entity = self.config.get("wandb.entity", "")
            project = self.config.get("wandb.project", "RL_race16")
            if entity:
                command.extend(["--wandb-entity", entity])
            command.extend(["--wandb-project-name", project])

        # Store total timesteps for progress calculation
        self._total_timesteps = timesteps

        process = self.processes.get_process("training")
        if process:
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_root
            # Add AAE_PATH for AutoencoderWrapper
            env["AAE_PATH"] = os.path.join(repo_root, "ae", "ae_mountain_pln_ur.pkl")
            
            # Setup logging for highscores
            # Predict the run ID that rl_zoo3 will use (e.g. donkey-mountain-track-v0_57)
            predicted_run_id = self._predict_next_run_id(repo_root, algo, env_name)
            
            env["RL_ZOO_LOG_DIR"] = os.path.join(repo_root, "logs")
            env["RL_ZOO_RUN_ID"] = predicted_run_id
            
            process.start(command, cwd=repo_root, env=env)

    def _stop_training(self) -> None:
        """Stop training."""
        process = self.processes.get_process("training")
        if process:
            process.stop()

    def _on_state_changed(self, state: ProcessState) -> None:
        """Handle training state changes.

        Args:
            state: New process state.
        """
        is_running = state == ProcessState.RUNNING
        self._start_btn.setEnabled(not is_running)
        self._stop_btn.setEnabled(is_running)

        if not is_running:
            self._progress_label.setText("Training stopped")

    # Signal for training metrics: episodes, mean_reward, mean_ep_length
    training_metrics_updated = pyqtSignal(int, float, float)

    def _parse_output(self, line: str) -> None:
        """Parse training output and update progress.

        Args:
            line: Output line from training process.
        """
        self.log(line)

        # Parse timesteps from output
        # Example: "| time/total_timesteps  | 50000 |"
        if "total_timesteps" in line.lower():
            try:
                parts = line.split("|")
                for i, part in enumerate(parts):
                    if "total_timesteps" in part.lower() and i + 1 < len(parts):
                        steps = int(parts[i + 1].strip())
                        if hasattr(self, "_total_timesteps"):
                            progress = int(
                                (steps / self._total_timesteps) * 100
                            )
                            self._progress_bar.setValue(min(progress, 100))
                        break
            except (ValueError, IndexError):
                pass
        
        # Parse metrics for monitor
        if "ep_rew_mean" in line and "|" in line:
            try:
                parts = line.split("|")
                val = float(parts[-2].strip())
                if not hasattr(self, "_current_reward"):
                     self._current_reward = 0.0
                self._current_reward = val
            except (ValueError, IndexError):
                pass
        
        if "ep_len_mean" in line and "|" in line:
             try:
                parts = line.split("|")
                val = float(parts[-2].strip())
                if not hasattr(self, "_current_len"):
                     self._current_len = 0.0
                self._current_len = val
             except (ValueError, IndexError):
                pass

        if "time/episodes" in line and "|" in line:
             try:
                parts = line.split("|")
                val = int(parts[-2].strip())
                if not hasattr(self, "_current_episodes"):
                     self._current_episodes = 0
                self._current_episodes = val
                
                # Emit signal when we have a new episode count
                rew = getattr(self, "_current_reward", 0.0)
                length = getattr(self, "_current_len", 0.0)
                self.training_metrics_updated.emit(val, rew, length)
             except (ValueError, IndexError):
                pass

        # Update label with episode info
        if "ep_rew_mean" in line.lower() or "episodes" in line.lower():
            self._progress_label.setText(line.strip()[:80])

    def _save_settings(self) -> None:
        """Save current settings."""
        self.config.set("environment.env_name", self._env_combo.currentText())
        self.config.set("training.algorithm", self._algo_combo.currentData())
        self.config.set("training.total_timesteps", self._timesteps_input.value())
        self.config.set("training.save_freq", self._save_freq_input.value())
        self.config.set("training.eval_freq", self._eval_freq_input.value())
        self.config.set("training.hyperparams_file", self._hyperparams_path.text())
        self.config.set("training.save_replay_buffer", self._replay_checkbox.isChecked())
        self.config.set("wandb.enabled", self._wandb_checkbox.isChecked())
        self.config.set("environment.steer_left", self._steer_left_input.value())
        self.config.set("environment.steer_right", self._steer_right_input.value())
        self.config.set("environment.throttle_min", self._throttle_min_input.value())
        self.config.set("environment.throttle_max", self._throttle_max_input.value())
        self.config.save()
        self.log("[Training] Settings saved")

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

    def on_show(self) -> None:
        """Called when module is shown."""
        self.config.load()
        self._update_ui_from_config()

    def _update_ui_from_config(self) -> None:
        """Update UI elements from configuration."""
        # Environment
        current_env = self.config.get("environment.env_name", "donkey-mountain-track-v0")
        index = self._env_combo.findText(current_env)
        if index >= 0:
            self._env_combo.setCurrentIndex(index)

        # Steering limits
        self._steer_left_input.setValue(
            self.config.get("environment.steer_left", -1.0)
        )
        self._steer_right_input.setValue(
            self.config.get("environment.steer_right", 1.0)
        )

        # Throttle limits
        self._throttle_min_input.setValue(
            self.config.get("environment.throttle_min", 0.0)
        )
        self._throttle_max_input.setValue(
            self.config.get("environment.throttle_max", 1.0)
        )

        # Algorithm
        current_algo = self.config.get("training.algorithm", "tqc")
        index = self._algo_combo.findData(current_algo)
        if index >= 0:
            self._algo_combo.setCurrentIndex(index)

        # Timesteps & Frequency
        self._timesteps_input.setValue(
            self.config.get("training.total_timesteps", 2000000)
        )
        self._save_freq_input.setValue(
            self.config.get("training.save_freq", 20000)
        )
        self._eval_freq_input.setValue(
            self.config.get("training.eval_freq", -1)
        )

        # Paths
        self._hyperparams_path.setText(
            self.config.get("training.hyperparams_file", "./hyperparams/tqc.yml")
        )

        # Options
        self._wandb_checkbox.setChecked(
            self.config.get("wandb.enabled", False)
        )
        self._replay_checkbox.setChecked(
            self.config.get("training.save_replay_buffer", True)
        )

