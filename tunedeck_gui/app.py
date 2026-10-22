"""
Application bootstrap and runner for TuneDeck GUI.
"""

import os
import sys
from typing import Optional

# Suppress benign Qt Wayland textinput warnings on Linux
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland.textinput=false;*.debug=false")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .theme import DARK_STYLESHEET
from .bridge import GuiControllerBridge
from .windows.main_window import MainWindow, create_app_icon


def create_application() -> QApplication:
    """Create and configure the Qt Application instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("TuneDeck")
    app.setApplicationDisplayName("TuneDeck — JBL Audio Controller")
    app.setOrganizationName("TuneDeck")
    app.setOrganizationDomain("tunedeck.github.io")
    app.setWindowIcon(create_app_icon())
    app.setStyleSheet(DARK_STYLESHEET)
    return app


def run_gui(
    simulate: bool = True,
    sim_model: str = "JBL Tune 770NC",
    address: Optional[str] = None,
) -> int:
    """Launch the GUI application."""
    app = create_application()

    bridge = GuiControllerBridge(
        simulate=simulate,
        sim_model=sim_model,
        address=address,
    )

    window = MainWindow(bridge)
    window.show()

    # Start controller connection
    bridge.start(auto_connect=True)

    return app.exec()
