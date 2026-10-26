"""
Application bootstrap and runner for TuneDeck GUI.
"""

import os
import sys
from typing import Optional

# Suppress benign Qt Wayland textinput warnings on Linux
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland.textinput=false;*.debug=false")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .theme import (
    DARK_STYLESHEET,
    COLOR_BG_DARK,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_JBL_ORANGE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
)
from .bridge import GuiControllerBridge
from .windows.main_window import MainWindow, create_app_icon


def _dark_palette() -> QPalette:
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: COLOR_BG_DARK,
        QPalette.ColorRole.Base: COLOR_BG_CARD,
        QPalette.ColorRole.AlternateBase: COLOR_BG_CARD_ALT,
        QPalette.ColorRole.Button: COLOR_BG_CARD_ALT,
        QPalette.ColorRole.WindowText: COLOR_TEXT_PRIMARY,
        QPalette.ColorRole.Text: COLOR_TEXT_PRIMARY,
        QPalette.ColorRole.ButtonText: COLOR_TEXT_PRIMARY,
        QPalette.ColorRole.ToolTipBase: COLOR_BG_CARD_ALT,
        QPalette.ColorRole.ToolTipText: COLOR_TEXT_PRIMARY,
        QPalette.ColorRole.PlaceholderText: COLOR_TEXT_MUTED,
        QPalette.ColorRole.Highlight: COLOR_JBL_ORANGE,
        QPalette.ColorRole.HighlightedText: "#FFFFFF",
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    return pal


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
    # Fusion + an explicit dark palette keep the look identical regardless of the
    # desktop's own (possibly light) theme.
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    app.setStyleSheet(DARK_STYLESHEET)
    return app


def run_gui(
    simulate: bool = False,
    model: Optional[str] = None,
    address: Optional[str] = None,
) -> int:
    """Launch the GUI application.

    Hardware mode by default: the paired JBL device is discovered and its
    profile chosen from its name. `model` overrides the profile in either mode.
    """
    app = create_application()

    bridge = GuiControllerBridge(
        simulate=simulate,
        sim_model=model,
        hw_model=model,
        address=address,
    )

    window = MainWindow(bridge)
    window.show()

    # Start controller connection
    bridge.start(auto_connect=True)

    exit_code = app.exec()
    bridge.shutdown()
    return exit_code
