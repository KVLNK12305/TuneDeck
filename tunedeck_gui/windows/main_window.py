"""
Main Application Window for TuneDeck GUI.
"""

from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QAction,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QStatusBar,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
)

from ..theme import (
    DARK_STYLESHEET,
    COLOR_BG_DARK,
    COLOR_JBL_ORANGE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)
from ..bridge import GuiControllerBridge
from ..widgets import (
    BatteryGaugeWidget,
    NoiseControlWidget,
    EqualizerWidget,
    HealthPanelWidget,
    DeviceBarWidget,
    DeviceSpotlightWidget,
)
from jblpc.protocol import NoiseMode, EQPreset


from pathlib import Path


def create_app_icon() -> QIcon:
    """Generate or load the official TuneDeck brand icon."""
    logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
    if logo_path.is_file():
        icon = QIcon(str(logo_path))
        if not icon.isNull():
            return icon

    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Orange rounded square background
    painter.setBrush(QColor(COLOR_JBL_ORANGE))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

    # Minimalist sleek white headphone vector
    painter.setPen(QPen(QColor("#FFFFFF"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(16, 14, 32, 32, 0, 180 * 16)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(14, 28, 8, 16, 4, 4)
    painter.drawRoundedRect(42, 28, 8, 16, 4, 4)
    painter.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    """Primary application window with tabs, controls, and system tray."""

    def __init__(self, bridge: GuiControllerBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.setWindowTitle("TuneDeck — JBL Audio Controller")
        self.resize(980, 740)
        self.setMinimumSize(880, 640)
        self.setStyleSheet(DARK_STYLESHEET)

        icon = create_app_icon()
        self.setWindowIcon(icon)

        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Device Bar
        self.device_bar = DeviceBarWidget(self)
        main_layout.addWidget(self.device_bar)

        # 2. Tabs
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(20, 16, 20, 16)
        main_layout.addWidget(self.tabs)

        # Tab 1: Sound & Controls
        sound_tab = QWidget()
        sound_layout = QVBoxLayout(sound_tab)
        sound_layout.setContentsMargins(0, 12, 0, 0)
        sound_layout.setSpacing(14)

        top_controls_row = QHBoxLayout()
        top_controls_row.setSpacing(14)

        # Left: Device Spotlight Card with actual product photo
        self.device_spotlight = DeviceSpotlightWidget(sound_tab)
        top_controls_row.addWidget(self.device_spotlight, 0)

        # Right: Battery & Noise Controls
        right_sub_col = QVBoxLayout()
        right_sub_col.setSpacing(14)
        self.battery_gauge = BatteryGaugeWidget(sound_tab)
        self.noise_control = NoiseControlWidget(sound_tab)
        right_sub_col.addWidget(self.battery_gauge, 1)
        right_sub_col.addWidget(self.noise_control, 1)
        top_controls_row.addLayout(right_sub_col, 1)

        sound_layout.addLayout(top_controls_row)

        self.eq_widget = EqualizerWidget(sound_tab)
        sound_layout.addWidget(self.eq_widget)
        sound_tab.setLayout(sound_layout)

        self.tabs.addTab(sound_tab, "Sound & Noise Control")

        # Tab 2: Battery Health Analytics
        health_tab = QWidget()
        health_layout = QVBoxLayout(health_tab)
        health_layout.setContentsMargins(0, 12, 0, 0)
        health_layout.setSpacing(14)

        self.health_panel = HealthPanelWidget(health_tab)
        health_layout.addWidget(self.health_panel)
        health_layout.addStretch()
        health_tab.setLayout(health_layout)

        self.tabs.addTab(health_tab, "Battery Health & Retention")

        # 3. Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("TuneDeck Ready")

        # 4. System Tray
        self._setup_system_tray(icon)

        # 5. Connect Signal Bindings
        self._wire_signals()

        # 6. Shortcuts (Ctrl+S on Windows/Linux, Cmd+S on macOS)
        save_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Save), self)
        save_shortcut.activated.connect(self._on_save_shortcut)

    def _setup_system_tray(self, icon: QIcon):
        """Configure system tray icon with quick actions."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("TuneDeck — JBL Controller")

        tray_menu = QMenu()
        self.tray_battery_action = QAction("Battery: --%", self)
        self.tray_battery_action.setEnabled(False)
        tray_menu.addAction(self.tray_battery_action)
        tray_menu.addSeparator()

        # Noise control submenu
        noise_menu = tray_menu.addMenu("Noise Control")
        for mode in [NoiseMode.ANC, NoiseMode.AMBIENT_AWARE, NoiseMode.TALKTHRU, NoiseMode.OFF]:
            act = QAction(mode.name.replace("_", " ").title(), self)
            act.triggered.connect(lambda checked=False, m=mode: self.bridge.set_noise_mode(m))
            noise_menu.addAction(act)

        tray_menu.addSeparator()
        toggle_act = QAction("Show / Hide Window", self)
        toggle_act.triggered.connect(self._toggle_window_visibility)
        tray_menu.addAction(toggle_act)

        quit_act = QAction("Quit TuneDeck", self)
        quit_act.triggered.connect(self.close)
        tray_menu.addAction(quit_act)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window_visibility()

    def _toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _wire_signals(self):
        """Wire UI events to Bridge and Bridge signals to UI."""
        # UI -> Bridge
        self.device_bar.model_switched.connect(self.bridge.switch_model)
        self.device_bar.simulation_toggled.connect(self.bridge.set_simulation_mode)
        self.device_bar.connect_requested.connect(self.bridge.connect_device)
        self.device_bar.disconnect_requested.connect(self.bridge.disconnect_device)
        self.device_bar.power_off_requested.connect(self.bridge.power_off)

        self.noise_control.mode_changed.connect(self.bridge.set_noise_mode)
        self.eq_widget.band_adjusted.connect(self.bridge.set_eq_band)
        self.eq_widget.preset_selected.connect(self.bridge.set_eq_preset)
        self.eq_widget.save_requested.connect(self.bridge.save_eq_to_config)

        self.health_panel.synthetic_requested.connect(self.bridge.generate_synthetic_history)

        # Bridge -> UI
        self.bridge.signals.state_updated.connect(self._on_state_updated)
        self.bridge.signals.health_updated.connect(self._on_health_updated)
        self.bridge.signals.connection_changed.connect(self._on_connection_changed)
        self.bridge.signals.error_occurred.connect(self._on_error_occurred)
        self.bridge.signals.power_off_completed.connect(self._on_power_off_completed)

    def _on_state_updated(self, state):
        self.device_spotlight.update_from_state(state)
        self.battery_gauge.update_from_state(state)
        self.noise_control.update_from_state(state)
        self.eq_widget.update_from_state(state)
        self.device_bar.set_active_model(state.profile.display_name)

        # Update tray battery text
        if self.tray_icon and self.tray_battery_action:
            if state.battery_level >= 0:
                self.tray_battery_action.setText(f"Battery: {state.battery_level}%")
            elif state.battery_left >= 0:
                self.tray_battery_action.setText(f"L:{state.battery_left}% R:{state.battery_right}% C:{state.battery_case}%")

        mode_desc = "Simulated" if self.bridge.simulate else "Hardware"
        self.status_bar.showMessage(
            f"Device: {state.profile.display_name} | Mode: {mode_desc} | Noise: {state.noise_mode_name} | EQ: {state.eq_preset_name}"
        )

    def _on_health_updated(self, report):
        self.health_panel.update_from_report(report)

    def _on_connection_changed(self, connected: bool, message: str):
        self.device_bar.update_connection_state(connected, message)
        self.status_bar.showMessage(f"Status: {message}")

    def _on_error_occurred(self, error_msg: str):
        self.status_bar.showMessage(f"Error: {error_msg}", 6000)

    def _on_power_off_completed(self):
        self.status_bar.showMessage("Device safely powered off", 8000)
        if self.tray_icon:
            self.tray_icon.showMessage("TuneDeck", "Device has powered off.", QSystemTrayIcon.MessageIcon.Information, 3000)

    def _on_save_shortcut(self):
        self.bridge.save_eq_to_config()
        self.status_bar.showMessage("Equalizer configuration saved to config.json", 4000)



