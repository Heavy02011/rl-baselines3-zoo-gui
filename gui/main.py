#!/usr/bin/env python3
"""Main entry point for the RL Racing GUI Control Center."""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.version import __version__


def main():
    """Launch the GUI application."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    # Enable high DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("RL Racing Control Center")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("ParkingLotNerds")

    # Import after QApplication is created
    from gui.ui.main_window import MainWindow

    window = MainWindow(gui_version=__version__)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
