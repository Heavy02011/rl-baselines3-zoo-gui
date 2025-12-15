"""Main application window for the RL Racing GUI."""
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.core.config_manager import ConfigManager
from gui.core.process_manager import ProcessManager, ProcessState
from gui.ui.log_panel import LogPanel
from gui.ui.modules.autoencoder_module import AutoencoderModule
from gui.ui.modules.collect_module import CollectModule
from gui.ui.modules.config_module import ConfigModule
from gui.ui.modules.dashboard_module import DashboardModule
from gui.ui.modules.drive_module import DriveModule
from gui.ui.modules.monitor_module import MonitorModule
from gui.ui.modules.simulator_module import SimulatorModule
from gui.ui.modules.training_module import TrainingModule
from gui.ui.modules.enjoy_module import EnjoyModule
from gui.ui.modules.highscores_module import HighscoresModule
from gui.ui.sidebar import Sidebar

TELEMETRY_PREFIX = "TELEMETRY:"
TRACKED_PROCESSES = ["simulator", "training", "drive", "collect", "autoencoder", "enjoy"]


class MainWindow(QMainWindow):
    """Main window for the RL Racing Control Center."""
    def __init__(self, gui_version: str = ""):
        """Initialize the main window."""
        super().__init__()
        self._gui_version = gui_version
        title_suffix = f" v{gui_version}" if gui_version else ""
        self.setWindowTitle(f"RL Racing Control Center{title_suffix}")
        self.setMinimumSize(1000, 700)
        self.setDockNestingEnabled(True)

        # Initialize managers
        gui_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(gui_dir, "config.yaml")
        self.config_manager = ConfigManager(config_path)
        self.process_manager = ProcessManager(self)

        # Set up UI
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

        # Load stylesheet
        self._load_stylesheet()

        # Select default module
        self._sidebar.select_module("dashboard")

        # Restore window geometry
        geometry = self.config_manager.get("gui.geometry")
        if geometry and len(geometry) == 4:
            self.setGeometry(*geometry)

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # Content area (stacked widget for modules)
        self._content_stack = QStackedWidget()
        self._modules: dict[str, QWidget] = {}

        # Create all modules
        self._modules["dashboard"] = DashboardModule(
            self.config_manager, self.process_manager
        )
        self._modules["simulator"] = SimulatorModule(
            self.config_manager, self.process_manager
        )
        self._modules["drive"] = DriveModule(
            self.config_manager, self.process_manager
        )
        self._modules["collect"] = CollectModule(
            self.config_manager, self.process_manager
        )
        self._modules["autoencoder"] = AutoencoderModule(
            self.config_manager, self.process_manager
        )
        self._modules["training"] = TrainingModule(
            self.config_manager, self.process_manager
        )
        self._modules["enjoy"] = EnjoyModule(
            self.config_manager, self.process_manager
        )
        self._modules["monitor"] = MonitorModule(
            self.config_manager, self.process_manager
        )
        self._modules["highscores"] = HighscoresModule(
            self.config_manager, self.process_manager
        )
        self._modules["config"] = ConfigModule(
            self.config_manager, self.process_manager
        )

        # Add modules to stack and connect log signals
        for module_id, module in self._modules.items():
            self._content_stack.addWidget(module)
            module.log_message.connect(self._on_log_message)

        # Connect training metrics to monitor
        training_module = self._modules.get("training")
        monitor_module = self._modules.get("monitor")
        if training_module and monitor_module and hasattr(training_module, "training_metrics_updated"):
            training_module.training_metrics_updated.connect(monitor_module.update_metrics)

        main_layout.addWidget(self._content_stack, 1)

        # Log panel (Dock Widget)
        self._log_dock = QDockWidget("Log Panel", self)
        self._log_dock.setObjectName("LogPanelDock")
        self._log_panel = LogPanel()
        self._log_dock.setWidget(self._log_panel)
        self._log_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._log_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)

    def _setup_menu(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        save_action = QAction("&Save Config", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        tb_action = QAction("Open &TensorBoard", self)
        tb_action.triggered.connect(self._open_tensorboard)
        tools_menu.addAction(tb_action)

        wandb_action = QAction("Open &W&&B Dashboard", self)
        wandb_action.triggered.connect(self._open_wandb)
        tools_menu.addAction(wandb_action)

        tools_menu.addSeparator()

        stop_all_action = QAction("&Stop All Processes", self)
        stop_all_action.triggered.connect(self._stop_all_processes)
        tools_menu.addAction(stop_all_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self) -> None:
        """Connect signals between components."""
        self._sidebar.module_selected.connect(self._show_module)

        # Connect process states to sidebar indicators and dashboard
        for name in TRACKED_PROCESSES:
            process = self.process_manager.get_process(name)
            if process is None:
                process = self.process_manager.create_process(name)
            process.state_changed.connect(
                lambda s, n=name: self._on_process_state(n, s)
            )

    def _load_stylesheet(self) -> None:
        """Load the Qt stylesheet."""
        gui_dir = os.path.dirname(os.path.dirname(__file__))
        style_path = os.path.join(gui_dir, "resources", "style.qss")

        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            # Default dark theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2d2d2d;
                    color: #d4d4d4;
                }
                QFrame {
                    background-color: #252525;
                    border: 1px solid #3d3d3d;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #5d5d5d;
                }
                QPushButton:disabled {
                    background-color: #2d2d2d;
                    color: #666666;
                }
                QLineEdit, QSpinBox, QComboBox {
                    background-color: #1e1e1e;
                    border: 1px solid #3d3d3d;
                    padding: 6px;
                    border-radius: 3px;
                }
                QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                    border-color: #0078d4;
                }
                QComboBox {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 6px;
                    border-radius: 3px;
                    selection-background-color: #0078d4;
                    selection-color: white;
                }
                QComboBox:hover {
                    border: 1px solid #0078d4;
                }
                QComboBox::drop-down {
                    border: 0px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #000000;
                    selection-background-color: #0078d4;
                    selection-color: #ffffff;
                    border: 1px solid #cccccc;
                    outline: 0;
                }
                QComboBox QAbstractItemView::item {
                    color: #000000;
                    background-color: #ffffff;
                    min-height: 25px;
                }
                QComboBox QAbstractItemView::item:selected {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                /* Force ListView to be white */
                QListView {
                    background-color: #ffffff;
                    color: #000000;
                }
                QTreeWidget, QTableWidget {
                    background-color: #1e1e1e;
                    alternate-background-color: #252525;
                    border: 1px solid #3d3d3d;
                }
                QHeaderView::section {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    padding: 5px;
                }
                QProgressBar {
                    border: 1px solid #3d3d3d;
                    border-radius: 3px;
                    background-color: #1e1e1e;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                }
                QMenuBar {
                    background-color: #2d2d2d;
                }
                QMenuBar::item:selected {
                    background-color: #3d3d3d;
                }
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                }
                QMenu::item:selected {
                    background-color: #0078d4;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
                QSplitter::handle {
                    background-color: #3d3d3d;
                }
            """)

    def _show_module(self, module_id: str) -> None:
        """Show a module panel.

        Args:
            module_id: ID of the module to show.
        """
        if module_id in self._modules:
            # Call on_hide for current module
            current_idx = self._content_stack.currentIndex()
            current_widget = self._content_stack.widget(current_idx)
            if hasattr(current_widget, "on_hide"):
                current_widget.on_hide()

            # Switch to new module
            module = self._modules[module_id]
            self._content_stack.setCurrentWidget(module)

            # Call on_show for new module
            if hasattr(module, "on_show"):
                module.on_show()

    def _on_log_message(self, message: str) -> None:
        """Handle log messages from modules.

        Args:
            message: Log message.
        """
        self._log_panel.append_log(message)
        dashboard = self._modules.get("dashboard")
        if dashboard and hasattr(dashboard, "append_log"):
            dashboard.append_log(message)

        if message.startswith(TELEMETRY_PREFIX):
            try:
                data = message.split(":", 1)[1].strip().split(",")
                if len(data) >= 2:
                    steering = float(data[0])
                    throttle = float(data[1])
                    dash_module = self._modules.get("dashboard")
                    if dash_module and hasattr(dash_module, "update_telemetry"):
                        dash_module.update_telemetry(steering, throttle)
            except (ValueError, IndexError):
                self._log_panel.append_error(
                    f"Telemetry parse failed for payload: {message}"
                )

    def _save_config(self) -> None:
        """Save configuration."""
        self.config_manager.save()
        self._log_panel.append_success("Configuration saved")

    def _open_tensorboard(self) -> None:
        """Open TensorBoard."""
        monitor = self._modules.get("monitor")
        if monitor and hasattr(monitor, "_open_tensorboard"):
            monitor._open_tensorboard()

    def _open_wandb(self) -> None:
        """Open W&B dashboard."""
        monitor = self._modules.get("monitor")
        if monitor and hasattr(monitor, "_open_wandb"):
            monitor._open_wandb()

    def _stop_all_processes(self) -> None:
        """Stop all running processes."""
        running = self.process_manager.get_running_processes()
        if running:
            reply = QMessageBox.question(
                self,
                "Stop All Processes",
                f"Stop {len(running)} running process(es)?\n\n"
                + "\n".join(running),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.process_manager.stop_all()
                self._log_panel.append_info("All processes stopped")
        else:
            self._log_panel.append_info("No processes running")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About RL Racing Control Center",
            "<h3>RL Racing Control Center</h3>"
            "<p>A GUI control center for the RL Racing pipeline.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Simulator control</li>"
            "<li>Manual driving</li>"
            "<li>Data collection</li>"
            "<li>Autoencoder training</li>"
            "<li>RL training with TQC/SAC/PPO</li>"
            "<li>Training monitoring</li>"
            "</ul>"
            "<p>Built with PyQt6</p>"
            f"<p><b>Version:</b> {self._gui_version or 'dev'}</p>"
            "<p>Release notes: see CHANGELOG.md</p>",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        running = self.process_manager.get_running_processes()
        if running:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                f"There are {len(running)} process(es) still running.\n"
                "Do you want to stop them and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.process_manager.stop_all()
                self._save_geometry()
                event.accept()
            else:
                event.ignore()
        else:
            self._save_geometry()
            event.accept()

    def _save_geometry(self) -> None:
        """Save window geometry to config."""
        geometry = self.geometry().getRect()
        self.config_manager.set("gui.geometry", geometry)
        self.config_manager.save()

    def _on_process_state(self, name: str, state: ProcessState) -> None:
        """Update UI on process state changes."""
        self._sidebar.set_status(name, state == ProcessState.RUNNING)
        dashboard = self._modules.get("dashboard")
        if dashboard and hasattr(dashboard, "set_process_state"):
            dashboard.set_process_state(name, state)
