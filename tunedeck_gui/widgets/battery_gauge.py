"""
Custom Battery Gauge Widget with Single-Unit and TWS Trio display modes.
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from jblpc.models import DeviceCategory
from ..theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_JBL_ORANGE,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_YELLOW,
    COLOR_ACCENT_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)


SINGLE_DIAL_LABELS = {
    DeviceCategory.OVER_EAR: "HEADPHONES",
    DeviceCategory.TWS: "EARBUDS",
    DeviceCategory.SPEAKER: "SPEAKER",
    DeviceCategory.PARTYBOX: "SPEAKER",
}


class CircularDial(QWidget):
    """A single antialiased circular battery dial."""

    def __init__(self, label: str = "BATTERY", size: int = 130, parent=None):
        super().__init__(parent)
        self.label = label
        self.dial_size = size
        self.level: int = -1
        self.charging: bool = False
        self.setFixedSize(size, size + 24)

    def set_state(self, level: int, charging: bool = False):
        self.level = level
        self.charging = charging
        self.update()

    def _get_level_color(self, level: int) -> QColor:
        if level <= 15:
            return QColor(COLOR_ACCENT_RED)
        elif level <= 35:
            return QColor(COLOR_ACCENT_YELLOW)
        elif level <= 70:
            return QColor(COLOR_JBL_ORANGE)
        else:
            return QColor(COLOR_ACCENT_GREEN)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.dial_size
        rect = QRectF(10, 10, w - 20, w - 20)
        thickness = 8

        # 1. Background Arc (Track)
        track_pen = QPen(QColor("#222530"), thickness)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        # 270 degree sweep from 225 deg to -45 deg
        start_angle = 225 * 16
        span_angle = -270 * 16
        painter.drawArc(rect, start_angle, span_angle)

        # 2. Foreground Arc (Active Level)
        if self.level >= 0:
            pct = min(100, max(0, self.level))
            active_span = int(-270 * 16 * (pct / 100.0))
            level_color = self._get_level_color(pct)

            fg_pen = QPen(level_color, thickness)
            fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(fg_pen)
            painter.drawArc(rect, start_angle, active_span)

        # 3. Center Text (Percentage & Charging Icon)
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        font = QFont("sans-serif", 16 if w >= 120 else 12, QFont.Weight.Bold)
        painter.setFont(font)

        if self.level >= 0:
            text = f"{self.level}%"
            if self.charging:
                text = f"{self.level}% (CHG)"
        else:
            text = "──"

        center_rect = QRectF(10, 10, w - 20, w - 20)
        painter.drawText(center_rect, Qt.AlignmentFlag.AlignCenter, text)

        # 4. Bottom Label
        painter.setPen(QColor(COLOR_TEXT_SECONDARY))
        lbl_font = QFont("sans-serif", 9, QFont.Weight.DemiBold)
        painter.setFont(lbl_font)
        lbl_rect = QRectF(0, w - 2, w, 24)
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, self.label)


class BatteryGaugeWidget(QWidget):
    """
    Battery status panel that automatically switches between
    single battery dial and TWS Trio (Left, Right, Case).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(18, 16, 18, 16)
        self._main_layout.setSpacing(12)

        # Header Title
        title_box = QHBoxLayout()
        title_lbl = QLabel("POWER & BATTERY")
        title_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY};")
        title_box.addWidget(self.status_lbl)
        self._main_layout.addLayout(title_box)

        # Dials container
        self.dials_layout = QHBoxLayout()
        self.dials_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dials_layout.setSpacing(24)
        self._main_layout.addLayout(self.dials_layout)

        # Single dial
        self.single_dial = CircularDial(label="HEADSET", size=130)
        self.dials_layout.addWidget(self.single_dial)

        # TWS Dials (Left, Right, Case)
        self.dial_left = CircularDial(label="LEFT", size=95)
        self.dial_right = CircularDial(label="RIGHT", size=95)
        self.dial_case = CircularDial(label="CASE", size=95)

        self.dial_left.hide()
        self.dial_right.hide()
        self.dial_case.hide()

        self.dials_layout.addWidget(self.dial_left)
        self.dials_layout.addWidget(self.dial_right)
        self.dials_layout.addWidget(self.dial_case)
        self._main_layout.addStretch()

    def update_from_state(self, state):
        """Update dial readings based on HeadsetState."""
        is_tws = state.shows_tws_trio

        if is_tws:
            self.single_dial.hide()
            self.dial_left.show()
            self.dial_right.show()
            self.dial_case.show()

            self.dial_left.set_state(state.battery_left)
            self.dial_right.set_state(state.battery_right)
            self.dial_case.set_state(state.battery_case)

            if state.battery_left >= 0 or state.battery_right >= 0:
                self.status_lbl.setText("TWS Earbuds Online")
            else:
                self.status_lbl.setText("Connecting...")
        else:
            self.dial_left.hide()
            self.dial_right.hide()
            self.dial_case.hide()
            self.single_dial.show()
            self.single_dial.label = SINGLE_DIAL_LABELS.get(state.profile.category, "BATTERY")

            self.single_dial.set_state(state.battery_level)
            if state.battery_level >= 0:
                self.status_lbl.setText(f"Active ({state.battery_level}%)")
            else:
                self.status_lbl.setText("Awaiting Telemetry")
