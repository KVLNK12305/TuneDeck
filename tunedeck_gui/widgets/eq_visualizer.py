"""
Interactive Multi-Band Graphic Equalizer with Smooth Spline Visualizer.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QLinearGradient,
    QFont,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QLabel,
    QPushButton,
    QFrame,
)

from jblpc.protocol import EQPreset, EQ_PRESET_NAMES
from jblpc.models import EQType
from ..theme import (
    COLOR_BG_DARK,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_JBL_ORANGE,
    COLOR_JBL_ORANGE_HOVER,
    COLOR_ACCENT_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)

FREQ_LABELS_10 = ["32", "64", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
FREQ_LABELS_5 = ["100", "300", "1k", "3k", "8k"]
FREQ_LABELS_3 = ["Bass", "Mid", "Treble"]

PRESET_BANDS = {
    EQPreset.FLAT: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    EQPreset.BASS: [6, 5, 4, 2, 0, 0, 0, 1, 2, 2],
    EQPreset.CLUB: [4, 3, 1, 0, 0, 2, 3, 4, 3, 2],
    EQPreset.VOCAL: [-2, -1, 0, 2, 4, 5, 4, 2, 0, -1],
    EQPreset.JAZZ: [3, 2, 1, 2, -1, -1, 0, 1, 2, 3],
}


class SplineCurveVisualizer(QWidget):
    """Draws a smooth cubic bezier audio response curve with glowing gradient."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.band_gains: list[int] = [0] * 10

    def set_gains(self, gains: list[int]):
        self.band_gains = list(gains)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self.band_gains)
        if n < 2:
            return

        # Background grid
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_DARK))

        # Center reference 0 dB line
        mid_y = h / 2.0
        grid_pen = QPen(QColor("#242834"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        # Calculate coordinates for each band (-12dB at bottom, +12dB at top)
        # Leave margins
        margin_x = 24.0
        usable_w = w - (margin_x * 2)
        step_x = usable_w / (n - 1)

        points: list[QPointF] = []
        for i, gain in enumerate(self.band_gains):
            x = margin_x + i * step_x
            # gain in [-12, 12] mapped to [h - 15, 15]
            norm = (gain + 12.0) / 24.0  # 0.0 to 1.0
            y = (h - 20) - (norm * (h - 40))
            points.append(QPointF(x, y))

        # Build smooth cubic bezier path
        curve_path = QPainterPath()
        curve_path.moveTo(points[0])

        for i in range(len(points) - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(len(points) - 1, i + 2)]

            # Catmull-Rom to Cubic Bezier control points
            c1_x = p1.x() + (p2.x() - p0.x()) / 6.0
            c1_y = p1.y() + (p2.y() - p0.y()) / 6.0
            c2_x = p2.x() - (p3.x() - p1.x()) / 6.0
            c2_y = p2.y() - (p3.y() - p1.y()) / 6.0

            curve_path.cubicTo(QPointF(c1_x, c1_y), QPointF(c2_x, c2_y), p2)

        # Gradient fill under the curve
        fill_path = QPainterPath(curve_path)
        fill_path.lineTo(points[-1].x(), h)
        fill_path.lineTo(points[0].x(), h)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(255, 102, 0, 90))
        gradient.setColorAt(0.7, QColor(255, 102, 0, 20))
        gradient.setColorAt(1.0, QColor(255, 102, 0, 0))

        painter.fillPath(fill_path, QBrush(gradient))

        # Draw glowing primary line
        line_pen = QPen(QColor(COLOR_JBL_ORANGE), 3)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.strokePath(curve_path, line_pen)

        # Draw point nodes
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        node_pen = QPen(QColor(COLOR_JBL_ORANGE), 2)
        painter.setPen(node_pen)
        for pt in points:
            painter.drawEllipse(pt, 4, 4)
        painter.end()


class EqualizerWidget(QWidget):
    """
    Equalizer visualizer and multi-band gain sliders with preset shortcuts.
    """
    band_adjusted = Signal(int, int)       # band_index, gain_db
    bands_batch_set = Signal(list)         # list[int]
    preset_selected = Signal(object)       # EQPreset
    save_requested = Signal()              # save to config

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(12)

        # Top Bar
        header_box = QHBoxLayout()
        title_lbl = QLabel("GRAPHIC EQUALIZER")
        title_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        header_box.addWidget(title_lbl)
        header_box.addStretch()

        self.preset_badge = QLabel("Flat")
        self.preset_badge.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_JBL_ORANGE};")
        header_box.addWidget(self.preset_badge)
        self._layout.addLayout(header_box)

        # Visualizer Curve
        self.visualizer = SplineCurveVisualizer()
        self._layout.addWidget(self.visualizer)

        # Sliders container
        self.sliders_frame = QFrame()
        self.sliders_layout = QHBoxLayout(self.sliders_frame)
        self.sliders_layout.setContentsMargins(0, 8, 0, 4)
        self.sliders_layout.setSpacing(6)
        self._layout.addWidget(self.sliders_frame)

        self.sliders: list[QSlider] = []
        self.gain_labels: list[QLabel] = []
        self.freq_labels: list[QLabel] = []
        self.col_widgets: list[QWidget] = []

        for i in range(10):
            col_widget = QWidget()
            col = QVBoxLayout(col_widget)
            col.setContentsMargins(0, 0, 0, 0)
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.setSpacing(4)

            # Gain text
            gain_lbl = QLabel("0")
            gain_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            gain_lbl.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_SECONDARY};")
            col.addWidget(gain_lbl)
            self.gain_labels.append(gain_lbl)

            # Vertical Slider
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setFixedHeight(95)
            slider.setCursor(Qt.CursorShape.PointingHandCursor)
            slider.valueChanged.connect(lambda val, idx=i: self._on_slider_moved(idx, val))
            col.addWidget(slider, alignment=Qt.AlignmentFlag.AlignCenter)
            self.sliders.append(slider)

            # Frequency Label
            freq_lbl = QLabel(FREQ_LABELS_10[i])
            freq_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            freq_lbl.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {COLOR_TEXT_MUTED};")
            col.addWidget(freq_lbl)
            self.freq_labels.append(freq_lbl)

            self.sliders_layout.addWidget(col_widget)
            self.col_widgets.append(col_widget)

        # Preset Buttons Row
        preset_box = QHBoxLayout()
        preset_box.setSpacing(6)
        self._layout.addLayout(preset_box)

        presets = [
            (EQPreset.FLAT, "Flat"),
            (EQPreset.BASS, "Bass Boost"),
            (EQPreset.CLUB, "Club"),
            (EQPreset.VOCAL, "Vocal"),
            (EQPreset.JAZZ, "Jazz"),
        ]

        self.preset_buttons: dict[EQPreset, QPushButton] = {}
        for preset, name in presets:
            btn = QPushButton(name)
            btn.setObjectName("segmentedItem")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, p=preset: self._on_preset_click(p))
            preset_box.addWidget(btn)
            self.preset_buttons[preset] = btn

        preset_box.addStretch()

        # Save Button
        self.save_btn = QPushButton("Save Preset (Ctrl+S)")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_requested.emit)
        preset_box.addWidget(self.save_btn)

        self._current_band_count = 10
        self._is_updating_ui = False

    def _setup_sliders(self, count: int, labels: list[str]):
        """Update visible slider columns without recreating widgets."""
        self._current_band_count = count
        for i, col_widget in enumerate(self.col_widgets):
            if i < count:
                lbl_text = labels[i] if i < len(labels) else f"B{i+1}"
                self.freq_labels[i].setText(lbl_text)
                col_widget.show()
            else:
                col_widget.hide()

    def _on_slider_moved(self, idx: int, value: int):
        if self._is_updating_ui:
            return
        self.gain_labels[idx].setText(f"{value:+d}" if value != 0 else "0")
        current_gains = [s.value() for s in self.sliders]
        self.visualizer.set_gains(current_gains)
        self.preset_badge.setText("Custom")
        self.band_adjusted.emit(idx, value)

    def _on_preset_click(self, preset: EQPreset):
        self.preset_selected.emit(preset)

    def update_from_state(self, state):
        """Update sliders and spline visualizer from HeadsetState."""
        profile = state.profile
        if profile.eq_type == EQType.NONE:
            self.hide()
            return
        self.show()

        labels = profile.eq_band_frequencies or ["Bass", "Mid", "Treble"]
        band_count = len(labels)

        if self._current_band_count != band_count:
            self._setup_sliders(band_count, labels)

        self._is_updating_ui = True
        gains = state.eq_bands[:band_count]
        if len(gains) < band_count:
            gains.extend([0] * (band_count - len(gains)))

        for i, val in enumerate(gains):
            if i < len(self.sliders):
                self.sliders[i].setValue(val)
                self.gain_labels[i].setText(f"{val:+d}" if val != 0 else "0")

        self.visualizer.set_gains(gains)
        self.preset_badge.setText(state.eq_preset_name)

        # Highlight active preset button if applicable
        for preset, btn in self.preset_buttons.items():
            if preset == state.eq_preset:
                btn.setObjectName("segmentedItemSelected")
            else:
                btn.setObjectName("segmentedItem")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._is_updating_ui = False
