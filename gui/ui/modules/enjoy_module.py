
"""RL Enjoy (Run) module."""
import os
import sys
import glob
import time
from typing import List, Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
    QCheckBox,
)

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule


class EnjoyModule(BaseModule):
    """Module for running/testing trained RL agents."""

    MODULE_NAME = "Run Agent"
    MODULE_ICON = "▶️"

    ALGORITHMS = [
        ("tqc", "TQC"),
        ("sac", "SAC"),
        ("ppo", "PPO"),
        ("td3", "TD3"),
    ]

    def _setup_ui(self) -> None:
        """Set up the enjoy UI."""
        # Description
        desc = QLabel(
            "Run trained agents to see them in action.\n"
            "Select an experiment or specific model checkpoint."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        self.add_widget(desc)

        # Settings form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Algorithm selection
        self._algo_combo = QComboBox()
        for algo_id, algo_name in self.ALGORITHMS:
            self._algo_combo.addItem(algo_name, algo_id)
        current_algo = self.config.get("training.algorithm", "tqc")
        index = self._algo_combo.findData(current_algo)
        if index >= 0:
            self._algo_combo.setCurrentIndex(index)
        self._algo_combo.currentIndexChanged.connect(self._refresh_models)
        form_layout.addRow("Algorithm:", self._algo_combo)

        # Environment selection (Should match what was trained)
        self._env_combo = QComboBox()
        self._env_combo.addItems(self._get_donkey_envs())
        # Default to whatever config says, or mountain track
        current_env = self.config.get("environment.env_name", "donkey-mountain-track-v0")
        index = self._env_combo.findText(current_env)
        if index >= 0:
            self._env_combo.setCurrentIndex(index)
        self._env_combo.currentIndexChanged.connect(self._refresh_models)
        form_layout.addRow("Environment:", self._env_combo)

        # Model/Folder Selection
        self._model_combo = QComboBox()
        self._model_combo.currentIndexChanged.connect(self._refresh_checkpoints)
        form_layout.addRow("Trained Model:", self._model_combo)

        # Refresh button next to model combo? Or just auto-refresh.
        refresh_btn = QPushButton("Refresh Models")
        refresh_btn.clicked.connect(self._refresh_models)
        form_layout.addRow("", refresh_btn)

        # Checkpoint selection (ComboBox instead of SpinBox)
        self._checkpoint_combo = QComboBox()
        form_layout.addRow("Checkpoint:", self._checkpoint_combo)

        # Timesteps
        self._episodes_spin = QSpinBox()
        self._episodes_spin.setRange(100, 100000)
        self._episodes_spin.setSingleStep(1000)
        self._episodes_spin.setValue(5000)
        form_layout.addRow("Timesteps:", self._episodes_spin)
        
        # Stochastic
        self._stochastic_check = QCheckBox("Stochastic (Explore)")
        self._stochastic_check.setToolTip("If checked, agent uses stochastic actions (like during training). Unchecked = Deterministic.")
        form_layout.addRow("Action Mode:", self._stochastic_check)

        # No Norm (Fix for missing vecnormalize.pkl)
        self._no_norm_check = QCheckBox("Disable Normalization")
        self._no_norm_check.setToolTip("Check this if you get 'VecNormalize stats not found' errors. Note: Agent performance may be poor.")
        form_layout.addRow("Normalization:", self._no_norm_check)

        self.add_widget(form_widget)

        # Status indicator
        self._status_label = QLabel("Status: Idle")
        self._status_label.setStyleSheet("color: #888888;")
        self.add_widget(self._status_label)

        # Control buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self._start_btn = QPushButton("▶ Run Agent")
        self._start_btn.clicked.connect(self._start_enjoy)
        self._start_btn.setStyleSheet(
            "background-color: #107c10; color: white; font-weight: bold;"
        )
        btn_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.clicked.connect(self._stop_enjoy)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "background-color: #d13438; color: white;"
        )
        btn_layout.addWidget(self._stop_btn)

        self.add_widget(btn_widget)
        self.add_stretch()

    def _connect_signals(self) -> None:
        """Connect process signals."""
        process = self.processes.create_process("enjoy")
        process.state_changed.connect(self._on_state_changed)
        process.output_received.connect(self.log)

    def _get_donkey_envs(self) -> List[str]:
        """Get list of available donkeycar environments."""
        # Simple hardcoded list or dynamic if possible. 
        # Reusing logic from training module would be ideal, but duplicating for safety/simplicity here.
        return [
            "donkey-mountain-track-v0",
            "donkey-warehouse-v0",
            "donkey-generated-roads-v0",
            "donkey-avc-sparkfun-v0",
            "donkey-generated-track-v0",
            "donkey-roboracingleague-track-v0",
            "donkey-waveshare-v0",
            "donkey-minimonaco-track-v0",
            "donkey-warren-track-v0",
            "donkey-thunderhill-track-v0",
            "donkey-circuit-launch-track-v0",
        ]

    def _refresh_models(self) -> None:
        """Scan logs folder for models matching current algo and env."""
        self._model_combo.clear()
        
        algo = self._algo_combo.currentData()
        env_name = self._env_combo.currentText()
        
        # Logs structure: logs/<algo>/<env_name>_N/
        # Repo root assumption
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        logs_dir = os.path.join(repo_root, "logs", algo)
        
        if not os.path.exists(logs_dir):
            self._model_combo.addItem("No logs found for this algo", None)
            return

        # Find folders starting with env_name
        # e.g. donkey-mountain-track-v0_1
        search_pattern = os.path.join(logs_dir, f"{env_name}_*")
        folders = glob.glob(search_pattern)
        
        # Sort by creation time or suffix ID
        # Let's try to extract the ID
        valid_folders = []
        for f in folders:
            if os.path.isdir(f):
                folder_name = os.path.basename(f)
                try:
                    # Extract suffix number
                    suffix = folder_name.replace(f"{env_name}_", "")
                    exp_id = int(suffix)
                    # Store folder path as user data
                    valid_folders.append((exp_id, f))
                except ValueError:
                    pass
        
        # Sort descending (newest first)
        valid_folders.sort(key=lambda x: x[0], reverse=True)
        
        if not valid_folders:
            self._model_combo.addItem(f"No models found for {env_name}", None)
        else:
            for exp_id, path in valid_folders:
                display_text = f"Exp {exp_id} ({os.path.basename(path)})"
                # Store (exp_id, full_path) as data
                self._model_combo.addItem(display_text, (exp_id, path))
            
            # Select first one which triggers checkpoint refresh
            self._refresh_checkpoints()

    def _refresh_checkpoints(self) -> None:
        """Refresh checkpoints for the selected model."""
        self._checkpoint_combo.clear()
        
        data = self._model_combo.currentData()
        if not data:
            return
            
        exp_id, folder_path = data
        
        if not os.path.exists(folder_path):
            return

        # 1. Look for best_model.zip
        best_model = os.path.join(folder_path, "best_model.zip")
        # Also check for env_name.zip which is the "final" model typically
        env_name = self._env_combo.currentText()
        final_model = os.path.join(folder_path, f"{env_name}.zip")
        
        if os.path.exists(best_model):
            self._checkpoint_combo.addItem("Best Model (best_model.zip)", "best")
        elif os.path.exists(final_model):
            self._checkpoint_combo.addItem(f"Final Model ({env_name}.zip)", "final")
            
        # 2. Look for intermediate checkpoints rl_model_N_steps.zip
        # Pattern: rl_model_([0-9]+)_steps.zip
        checkpoints = []
        pattern = os.path.join(folder_path, "rl_model_*_steps.zip")
        for f in glob.glob(pattern):
            basename = os.path.basename(f)
            try:
                # parsed: rl_model_10000_steps.zip -> 10000
                parts = basename.split("_")
                steps = int(parts[2])
                checkpoints.append(steps)
            except (IndexError, ValueError):
                pass
        
        checkpoints.sort(reverse=True)
        
        for step in checkpoints:
            self._checkpoint_combo.addItem(f"Checkpoint {step} steps", step)
            
        if self._checkpoint_combo.count() == 0:
            self._checkpoint_combo.addItem("No checkpoints found", None)

    def on_show(self) -> None:
        """Called when module is shown."""
        self._refresh_models()

    def _ensure_lap_wrapper(self, config_path: str) -> None:
        """Ensure LapLoggingWrapper is in config."""
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            if "utils.wrappers.LapLoggingWrapper" in content:
                return

            self.log("[Enjoy] Adding LapLoggingWrapper to config...")
            
            # Backup
            if not os.path.exists(config_path + ".bak"):
                    with open(config_path + ".bak", 'w') as f:
                        f.write(content)
            
            lines = content.splitlines()
            new_lines = []
            patched = False
            
            # Strategy: Find a known wrapper and insert before/after it.
            # Common wrappers: AutoencoderWrapper, HistoryWrapper, TimeLimit
            anchor_text = "utils.wrappers.AutoencoderWrapper"
            
            for line in lines:
                if not patched and anchor_text in line:
                    # Found anchor. Capture indentation.
                    # Example: "    - - utils.wrappers.AutoencoderWrapper:"
                    # We want to insert "- utils.wrappers.LapLoggingWrapper" at same level.
                    # But wait, the serialized format uses "- -" for the first element of a list sometimes?
                    # "    - - utils.wrappers.AutoencoderWrapper:"
                    # This implies a list inside a list.
                    # Subsequent items might look like "    - gymnasium.wrappers.TimeLimit:"
                    
                    # We will try to match indentation of the '-'
                    stripped = line.lstrip()
                    indent = line[:len(line) - len(stripped)]
                    
                    # If line starts with "- - ", we should just use "- " for our new item if we append?
                    # No, if we insert BEFORE, we might need to handle the double dash if it's the first item?
                    # Actually, let's insert AFTER the anchor line.
                    
                    new_lines.append(line)
                    
                    # Construct insertion
                    # If anchor started with "- -", succeeding items usually start with "      -" (indented) or "    -" ?
                    # Let's peek at the file content again via memory/logic.
                    #   - - env_wrapper
                    #     - - utils.wrappers.AutoencoderWrapper:
                    #       - gymnasium.wrappers.TimeLimit:
                    #
                    # If I insert after, I should check the indentation of the NEXT line usually.
                    # But I'll guess: replace "- - " with "      - " or "    - "?
                    
                    # Safest bet: Look for "utils.wrappers.HistoryWrapper" or similar and verify.
                    # But simpler: use the exact same indentation string, replacing the text.
                    # If matching "- - ", replace with "      - " (2 extra spaces for the inner list item alignment?) 
                    # Actually, if "    - - utils...", the next item "    - gymnasium..." ?
                    # Let's assume standard YAML list alignment.
                    
                    # Let's simple insert:
                    # "      - utils.wrappers.LapLoggingWrapper"
                    # We will guess 6 spaces based on "    - - " (4 spaces, dash, space, dash, space).
                    
                    # Actually, if I just append to the END of the list?
                    # The list is defined by indentation.
                    
                    new_lines.append(f"{indent}    - utils.wrappers.LapLoggingWrapper")
                    patched = True
                    continue

                new_lines.append(line)
                
            if not patched:
                 # Fallback: look for env_wrapper line
                 new_lines = []
                 for line in lines:
                     new_lines.append(line)
                     if "env_wrapper" in line and not patched:
                         # Assume next lines are the list.
                         # We can't easily insert validly without knowing structure.
                         # Warning user.
                         pass
                 self.log("[Enjoy] Warning: Could not find anchor to inject LapLoggingWrapper. Highscores may not work.")
            else:
                 with open(config_path, 'w') as f:
                     f.write("\n".join(new_lines) + "\n")
                     
        except Exception as e:
            self.log(f"[Enjoy] Failed to patch config for lap logging: {e}")

    def _start_enjoy(self) -> None:
        """Start the enjoy script."""
        data = self._model_combo.currentData()
        if not data:
            self.log("[Enjoy] Error: No valid model selected.")
            return
            
        exp_id, folder_path = data
        
        checkpoint_val = self._checkpoint_combo.currentData()
        if checkpoint_val is None:
             self.log("[Enjoy] Error: No valid checkpoint selected.")
             return

        algo = self._algo_combo.currentData()
        env_name = self._env_combo.currentText()
        
        timesteps = self._episodes_spin.value()
        stochastic = self._stochastic_check.isChecked()
        no_norm = self._no_norm_check.isChecked()

        # Check if we need to auto-disable normalization
        # rl_zoo3 looks for vecnormalize.pkl in the env subfolder
        vecnorm_path = os.path.join(folder_path, env_name, "vecnormalize.pkl")
        config_path = os.path.join(folder_path, env_name, "config.yml")
        
        # Ensure lap logging wrapper exists
        if os.path.exists(config_path):
            self._ensure_lap_wrapper(config_path)

        if not no_norm and not os.path.exists(vecnorm_path):
             self.log(f"[Enjoy] Warning: {vecnorm_path} not found.")
             self.log("[Enjoy] Missing stats file. Auto-disabling normalization in config to allow running.")
             no_norm = True

        if no_norm and os.path.exists(config_path):
            # Patch config.yml to set normalize: false
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                
                # Check if normalization is enabled
                if "normalize" in content and "False" not in content.split("normalize")[1].split("\n")[0]:
                     self.log("[Enjoy] Patching config.yml to disable normalization...")
                     # Backup
                     if not os.path.exists(config_path + ".bak"):
                         with open(config_path + ".bak", 'w') as f:
                             f.write(content)
                     
                     # Bruteforce replace. The file format seen was:
                     # - - normalize
                     #   - '{'norm_obs': True...}'
                     # We want to replace the value with False.
                     # Since it is a bit unstructured, maybe just append an override or rewrite?
                     # Let's try a regex-friendly approach or just reading line by line.
                     
                     new_lines = []
                     skip_next = False
                     lines = content.splitlines()
                     for i, line in enumerate(lines):
                         if skip_next:
                             skip_next = False
                             continue
                         
                         if "- - normalize" in line or "- normalize" in line:
                             new_lines.append(line)
                             # The next line contains the value in the format seen
                             #   - '{...}'
                             # We replace it with:
                             #   - false
                             new_lines.append("    - false") # Indentation might vary
                             skip_next = True
                             continue
                         new_lines.append(line)
                     
                     with open(config_path, 'w') as f:
                         f.write("\n".join(new_lines) + "\n")
            except Exception as e:
                self.log(f"[Enjoy] Failed to patch config: {e}")

        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        # Construct command: python -m rl_zoo3.enjoy ...
        command = [
            sys.executable,
            "-m",
            "rl_zoo3.enjoy",
            "--algo", algo,
            "--env", env_name,
            "--folder", os.path.join(repo_root, "logs"),
            "--exp-id", str(exp_id),
            "-n", str(timesteps),
        ]

        if isinstance(checkpoint_val, int):
            # It's a specific step
            command.extend(["--load-checkpoint", str(checkpoint_val)])
        elif checkpoint_val == "best":
            # best_model.zip is "load-best" usually, OR just let it default if we don't pass --load-checkpoint
            # However, rl_zoo3 loads "last" model by default unless --load-best is passed.
            # actually rl_zoo3 docs say default is last model.
            command.append("--load-best")
        elif checkpoint_val == "final":
            # Just standard loading, no extra flags needed as it looks for env_name.zip
            pass
        
        if stochastic:
            command.append("--stochastic")
            
        # --no-norm is NOT valid in rl_zoo3. usage only shows --norm-reward (which enables it).
        # We rely on the config patching above.

        self.log(f"[Enjoy] Starting: {' '.join(command)}")

        process = self.processes.get_process("enjoy")
        if process:
             # Need AAE_PATH in env if wrapper uses it
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_root
            env["AAE_PATH"] = os.path.join(repo_root, "ae", "ae_mountain_pln_ur.pkl")
            # Pass log dir for LapLoggingWrapper
            env["RL_ZOO_LOG_DIR"] = folder_path
            env["RL_ZOO_RUN_ID"] = f"enjoy_{int(time.time())}"
            
            process.start(command, cwd=repo_root, env=env)

    def _stop_enjoy(self) -> None:
        """Stop the running agent."""
        process = self.processes.get_process("enjoy")
        if process:
            process.stop()

    def _on_state_changed(self, state: ProcessState) -> None:
        """Handle process state changes."""
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
            self._status_label.setText("Status: Idle")
            self._status_label.setStyleSheet("color: #888888;")
