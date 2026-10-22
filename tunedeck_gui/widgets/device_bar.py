"""
Device status header bar with model switcher, connection toggles, and power-off.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QMessageBox,
    QCheckBox,
)

from jblpc.models import SUPPORTED_MODELS
from ..theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_JBL_ORANGE,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)


class DeviceBarWidget(QWidget):
    """
    Top status bar displaying device identity, model selection,
    simulation mode toggle, and power controls.
    """
    model_switched = Signal(str)           # model name
    simulation_toggled = Signal(bool)      # is_sim
    connect_requested = Signal()           # connect
    disconnect_requested = Signal()        # disconnect
    power_off_requested = Signal()         # power off

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            DeviceBarWidget {{
                background-color: {COLOR_BG_CARD};
                border-bottom: 1px solid {COLOR_BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        # Brand / Logo
        logo_lbl = QLabel("TUNEDECK")
        logo_lbl.setStyleSheet(f"font-size: 15px; font-weight: 900; color: {COLOR_JBL_ORANGE}; letter-spacing: 1.5px;")
        layout.addWidget(logo_lbl)

        # Connection status dot & label
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {COLOR_ACCENT_GREEN}; font-size: 14px;")
        layout.addWidget(self.status_dot)

        self.status_text = QLabel("Connected")
        self.status_text.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(self.status_text)

        layout.addSpacing(10)

        # Model Selector Dropdown
        layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(180)
        for profile in SUPPORTED_MODELS:
            self.model_combo.addItem(profile.display_name, profile.display_name)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.model_combo)

        # Simulator Checkbox
        self.sim_check = QCheckBox("Simulation Mode")
        self.sim_check.setChecked(True)
        self.sim_check.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        self.sim_check.toggled.connect(self.simulation_toggled.emit)
        layout.addWidget(self.sim_check)

        layout.addStretch()

        # Connect / Disconnect button
        self.conn_btn = QPushButton("Disconnect")
        self.conn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.conn_btn.clicked.connect(self._on_conn_toggle)
        layout.addWidget(self.conn_btn)

        # Power Off Button
        self.power_btn = QPushButton("Power Off")
        self.power_btn.setObjectName("dangerButton")
        self.power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.power_btn.clicked.connect(self._on_power_off_click)
        layout.addWidget(self.power_btn)

        self._connected = True

    def _on_model_changed(self, text: str):
        if text:
            self.model_switched.emit(text)

    def _on_conn_toggle(self):
        if self._connected:
            self.disconnect_requested.emit()
        else:
            self.connect_requested.emit()

    def _on_power_off_click(self):
        reply = QMessageBox.question(
            self,
            "Confirm Power Off",
            "Are you sure you want to send the remote power-off command to your JBL device?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.power_off_requested.emit()

    def update_connection_state(self, connected: bool, message: str = ""):
        self._connected = connected
        if connected:
            self.status_dot.setStyleSheet(f"color: {COLOR_ACCENT_GREEN}; font-size: 14px;")
            self.status_text.setText(message or "Connected")
            self.conn_btn.setText("Disconnect")
            self.power_btn.setEnabled(True)
        else:
            self.status_dot.setStyleSheet(f"color: {COLOR_ACCENT_RED}; font-size: 14px;")
            self.status_text.setText(message or "Disconnected")
            self.conn_btn.setText("Connect")
            self.power_btn.setEnabled(False)

    def set_active_model(self, model_name: str):
        idx = self.model_combo.findText(model_name)
        if idx >= 0:
            self.model_combo.blockSignals(True)
            self.model_combo.setCurrentIndex(idx)
            self.model_combo.blockSignals(False)
