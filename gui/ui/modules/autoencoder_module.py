"""Autoencoder training module."""
import os
import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
import cv2
import numpy as np
import glob
from gym_donkeycar.autoencoder import load_ae, preprocess_image

from gui.core.process_manager import ProcessState
from gui.ui.modules.base_module import BaseModule


class ReconstructionDialog(QDialog):
    """Dialog to visualize autoencoder reconstruction."""

    def __init__(self, parent, model_path: str, images_folder: str):
        super().__init__(parent)
        self.setWindowTitle("Reconstruction Visualization")
        self.setModal(True)
        self.resize(800, 400)

        self.model_path = model_path
        self.images_folder = images_folder
        
        # Load images
        self.image_paths = glob.glob(os.path.join(images_folder, "*.jpg")) + \
                           glob.glob(os.path.join(images_folder, "*.png"))
        
        if not self.image_paths:
            QMessageBox.warning(self, "No Images", "No .jpg or .png images found in the selected folder.")
            self.reject()
            return

        # Load model
        try:
            self.model = load_ae(model_path)
            self.model.eval()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model:\n{str(e)}")
            self.reject()
            return

        self._setup_ui()
        self._load_random_image()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Images area
        imgs_layout = QHBoxLayout()
        
        # Original
        orig_layout = QVBoxLayout()
        orig_layout.addWidget(QLabel("Original"))
        self.orig_label = QLabel()
        self.orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orig_label.setMinimumSize(320, 240)
        self.orig_label.setStyleSheet("border: 1px solid #444; background: #000;")
        orig_layout.addWidget(self.orig_label)
        imgs_layout.addLayout(orig_layout)

        # Reconstructed
        recon_layout = QVBoxLayout()
        recon_layout.addWidget(QLabel("Reconstructed"))
        self.recon_label = QLabel()
        self.recon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recon_label.setMinimumSize(320, 240)
        self.recon_label.setStyleSheet("border: 1px solid #444; background: #000;")
        recon_layout.addWidget(self.recon_label)
        imgs_layout.addLayout(recon_layout)

        layout.addLayout(imgs_layout)

        # Controls
        controls_layout = QHBoxLayout()
        
        self.next_btn = QPushButton("Next Random Image")
        self.next_btn.clicked.connect(self._load_random_image)
        controls_layout.addWidget(self.next_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        controls_layout.addWidget(close_btn)

        layout.addLayout(controls_layout)

    def _load_random_image(self):
        if not self.image_paths:
            return

        # Pick random image
        path = np.random.choice(self.image_paths)
        
        # Read image (BGR)
        img = cv2.imread(path)
        if img is None:
            return

        # Process for display (Original)
        # Resize to reasonable size for display if too small/large
        disp_orig = cv2.resize(img, (320, 240))
        self._display_image(disp_orig, self.orig_label)

        # Process for AE
        # encode_from_raw_image expects BGR, handles preprocessing
        try:
            # Encode
            latent = self.model.encode_from_raw_image(img)
            # Decode
            recon = self.model.decode(latent)[0]
            
            # Recon is BGR, [0, 255] uint8
            disp_recon = cv2.resize(recon, (320, 240))
            self._display_image(disp_recon, self.recon_label)
            
        except Exception as e:
            print(f"Reconstruction error: {e}")

    def _display_image(self, img_bgr, label):
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(qimg))


class AutoencoderModule(BaseModule):
    """Module for autoencoder training and management."""

    MODULE_NAME = "Autoencoder"
    MODULE_ICON = "🧠"

    def _setup_ui(self) -> None:
        """Set up the autoencoder UI."""
        # Description
        desc = QLabel(
            "Train an autoencoder to compress camera images.\n"
            "Used to reduce observation space for RL training."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-bottom: 10px;")
        self.add_widget(desc)

        # Current model section
        self.add_widget(QLabel("Current Model:"))
        model_widget = QWidget()
        model_layout = QHBoxLayout(model_widget)
        model_layout.setContentsMargins(0, 0, 0, 0)

        self._model_path = QLineEdit()
        self._model_path.setText(
            self.config.get("autoencoder.model_path", "")
        )
        self._model_path.setReadOnly(True)
        model_layout.addWidget(self._model_path)

        load_btn = QPushButton("Load...")
        load_btn.clicked.connect(self._load_model)
        model_layout.addWidget(load_btn)

        self.add_widget(model_widget)

        # Training images folder
        self.add_widget(QLabel("Training Images Folder:"))
        images_widget = QWidget()
        images_layout = QHBoxLayout(images_widget)
        images_layout.setContentsMargins(0, 0, 0, 0)

        self._images_folder = QLineEdit()
        self._images_folder.setPlaceholderText("Select folder with training images...")
        images_layout.addWidget(self._images_folder)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_images)
        images_layout.addWidget(browse_btn)

        self.add_widget(images_widget)

        # Training parameters
        params_widget = QWidget()
        params_layout = QFormLayout(params_widget)
        params_layout.setContentsMargins(0, 10, 0, 10)

        # Epochs
        self._epochs_input = QSpinBox()
        self._epochs_input.setRange(1, 1000)
        self._epochs_input.setValue(100)
        params_layout.addRow("Epochs:", self._epochs_input)

        # Batch size
        self._batch_input = QSpinBox()
        self._batch_input.setRange(1, 512)
        self._batch_input.setValue(64)
        params_layout.addRow("Batch Size:", self._batch_input)

        # Z size (latent dimension)
        self._z_size_input = QSpinBox()
        self._z_size_input.setRange(8, 256)
        self._z_size_input.setValue(
            self.config.get("autoencoder.z_size", 32)
        )
        params_layout.addRow("Latent Dimension (z):", self._z_size_input)

        self.add_widget(params_widget)

        # Progress bar
        self.add_widget(QLabel("Training Progress:"))
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self.add_widget(self._progress_bar)

        self._progress_label = QLabel("Epoch: 0/0 | Loss: -")
        self._progress_label.setStyleSheet("color: #888888;")
        self.add_widget(self._progress_label)

        # Training buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self._train_btn = QPushButton("▶ Start Training")
        self._train_btn.clicked.connect(self._start_training)
        btn_layout.addWidget(self._train_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.clicked.connect(self._stop_training)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)

        self.add_widget(btn_widget)

        # Additional buttons
        btn_widget2 = QWidget()
        btn_layout2 = QHBoxLayout(btn_widget2)
        btn_layout2.setContentsMargins(0, 0, 0, 0)

        test_btn = QPushButton("🔍 Test Reconstruction")
        test_btn.clicked.connect(self._test_reconstruction)
        btn_layout2.addWidget(test_btn)

        self.add_widget(btn_widget2)

        # Save settings
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        self.add_widget(save_btn)

        self.add_stretch()

    def _connect_signals(self) -> None:
        """Connect process signals."""
        process = self.processes.create_process("autoencoder")
        process.state_changed.connect(self._on_state_changed)
        process.output_received.connect(self._parse_output)

    def _load_model(self) -> None:
        """Load an existing autoencoder model."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Autoencoder Model",
            "",
            "Pickle Files (*.pkl);;All Files (*)",
        )
        if path:
            self._model_path.setText(path)
            self.config.set("autoencoder.model_path", path)
            self.log(f"[Autoencoder] Loaded model: {path}")

    def _browse_images(self) -> None:
        """Browse for training images folder."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Training Images Folder"
        )
        if path:
            self._images_folder.setText(path)

    def _start_training(self) -> None:
        """Start autoencoder training."""
        images_folder = self._images_folder.text()
        if not images_folder or not os.path.exists(images_folder):
            self.log("[Autoencoder] Error: Invalid images folder")
            return

        self.log("[Autoencoder] Starting training...")

        # Get training parameters
        epochs = self._epochs_input.value()
        batch_size = self._batch_input.value()
        z_size = self._z_size_input.value()

        # Build command
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )

        command = [
            sys.executable,
            "-m",
            "ae.train_ae",
            "--n-epochs",
            str(epochs),
            "--batch-size",
            str(batch_size),
            "--z-size",
            str(z_size),
            "-f",
            images_folder,
        ]

        process = self.processes.get_process("autoencoder")
        if process:
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_root
            process.start(command, cwd=repo_root, env=env)

    def _stop_training(self) -> None:
        """Stop autoencoder training."""
        process = self.processes.get_process("autoencoder")
        if process:
            process.stop()

    def _on_state_changed(self, state: ProcessState) -> None:
        """Handle training state changes.

        Args:
            state: New process state.
        """
        is_running = state == ProcessState.RUNNING
        self._train_btn.setEnabled(not is_running)
        self._stop_btn.setEnabled(is_running)

        if not is_running:
            self._progress_bar.setValue(0)
            self._progress_label.setText("Training stopped")

    def _parse_output(self, line: str) -> None:
        """Parse training output and update progress.

        Args:
            line: Output line from training process.
        """
        self.log(line)

        # Parse epoch progress (example: "Epoch 50/100, Loss: 0.0123")
        if "Epoch" in line and "/" in line:
            try:
                parts = line.split()
                for part in parts:
                    if "/" in part:
                        current, total = part.split("/")
                        current = int(current.replace(",", ""))
                        total = int(total.replace(",", ""))
                        progress = int((current / total) * 100)
                        self._progress_bar.setValue(progress)
                        break

                # Update label
                self._progress_label.setText(line.strip())
            except (ValueError, IndexError):
                pass

    def _test_reconstruction(self) -> None:
        """Test reconstruction on sample images."""
        from PyQt6.QtWidgets import QMessageBox

        model_path = self._model_path.text()
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(
                self,
                "No Model Loaded",
                "Please load an autoencoder model first.",
            )
            return

        self.log("[Autoencoder] Test reconstruction - feature not yet implemented")

        images_folder = self._images_folder.text()
        if not images_folder or not os.path.exists(images_folder):
             QMessageBox.warning(
                self,
                "No Images Folder",
                "Please select a valid training images folder.",
            )
             return

        dialog = ReconstructionDialog(self, model_path, images_folder)
        dialog.exec()

    def _save_settings(self) -> None:
        """Save current settings."""
        self.config.set("autoencoder.model_path", self._model_path.text())
        self.config.set("autoencoder.z_size", self._z_size_input.value())
        self.config.save()
        self.log("[Autoencoder] Settings saved")
