"""
Battery Health, Retention Analytics, and Cycle Estimation Panel.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
)

from jblpc.health import DeviceHealthReport, ComponentHealth
from ..theme import (
    COLOR_BG_DARK,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
    COLOR_JBL_ORANGE,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_YELLOW,
    COLOR_ACCENT_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)


class MetricCard(QFrame):
    """Stat card for displaying health telemetry."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        # Scoped by object name: a bare "QFrame" selector also matches the QLabel children.
        self.setObjectName("metricCard")
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {COLOR_BG_CARD_ALT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px;")
        layout.addWidget(self.title_lbl)

        self.val_lbl = QLabel("──")
        self.val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(self.val_lbl)

        self.sub_lbl = QLabel("Calculating...")
        self.sub_lbl.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(self.sub_lbl)

    def set_value(self, val: str, sub: str = "", color: Optional[str] = None):
        self.val_lbl.setText(val)
        if color:
            self.val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color};")
        else:
            self.val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        if sub:
            self.sub_lbl.setText(sub)


class HealthPanelWidget(QWidget):
    """
    Displays battery wear, equivalent full cycles (EFC), discharge efficiency,
    and confidence scores.
    """
    synthetic_requested = Signal(str)  # scenario name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(14)

        # Header Title
        title_box = QHBoxLayout()
        title_lbl = QLabel("BATTERY HEALTH & RETENTION ANALYTICS")
        title_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self.confidence_badge = QLabel("CONFIDENCE: PENDING")
        self.confidence_badge.setStyleSheet(f"""
            background-color: #262936;
            color: {COLOR_TEXT_SECONDARY};
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        title_box.addWidget(self.confidence_badge)
        self._layout.addLayout(title_box)

        # Cards Grid
        grid = QGridLayout()
        grid.setSpacing(10)
        self._layout.addLayout(grid)

        self.card_efc = MetricCard("Estimated Cycles (EFC)")
        self.card_discharge = MetricCard("Active Discharge Rate")
        self.card_retention = MetricCard("Retention Degradation")
        self.card_samples = MetricCard("Telemetry History")

        grid.addWidget(self.card_efc, 0, 0)
        grid.addWidget(self.card_discharge, 0, 1)
        grid.addWidget(self.card_retention, 1, 0)
        grid.addWidget(self.card_samples, 1, 1)

        # Disclaimer Box
        disclaimer_box = QFrame()
        disclaimer_box.setObjectName("disclaimerBox")
        disclaimer_box.setStyleSheet(f"""
            QFrame#disclaimerBox {{
                background-color: rgba(255, 102, 0, 0.08);
                border-left: 3px solid {COLOR_JBL_ORANGE};
                padding: 6px 10px;
                border-radius: 4px;
            }}
        """)
        disc_layout = QVBoxLayout(disclaimer_box)
        disc_layout.setContentsMargins(6, 4, 6, 4)
        self.note_lbl = QLabel("EFC is mathematically derived as sum(Δ upward charge movements) / 100. Discharges calculated during active playback.")
        self.note_lbl.setWordWrap(True)
        self.note_lbl.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_SECONDARY}; line-height: 1.4;")
        disc_layout.addWidget(self.note_lbl)
        self._layout.addWidget(disclaimer_box)

        # Testing & Simulation Toolbar
        sim_bar = QHBoxLayout()
        sim_bar.setSpacing(8)
        sim_lbl = QLabel("Test Synthetic Profile:")
        sim_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        sim_bar.addWidget(sim_lbl)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(["healthy", "degraded", "gaps", "clock_jumps"])
        sim_bar.addWidget(self.scenario_combo)

        gen_btn = QPushButton("Inject Test Data")
        gen_btn.setObjectName("segmentedItem")
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.clicked.connect(self._on_inject_clicked)
        sim_bar.addWidget(gen_btn)

        sim_bar.addStretch()
        self._layout.addLayout(sim_bar)

    def _on_inject_clicked(self):
        scenario = self.scenario_combo.currentText()
        self.synthetic_requested.emit(scenario)

    def update_from_report(self, report: Optional[DeviceHealthReport]):
        """Render metrics from health report."""
        if not report or not report.components:
            return

        # Get primary component ('single', 'left', or first component)
        comp = report.components.get("single") or report.components.get("left") or next(iter(report.components.values()))

        # Cycles
        self.card_efc.set_value(f"{comp.estimated_cycles:.1f}", "Full charge cycles")

        # Discharge rate
        if comp.discharge_rate_pct_per_hr is not None:
            rate = comp.discharge_rate_pct_per_hr
            col = COLOR_ACCENT_GREEN if rate < 12 else (COLOR_ACCENT_YELLOW if rate < 20 else COLOR_ACCENT_RED)
            self.card_discharge.set_value(f"{rate:.1f} %/hr", "Active playback rate", color=col)
        else:
            self.card_discharge.set_value("Calculating...", "Need more playback data")

        # Retention
        if comp.retention_trend_pct is not None:
            ret = comp.retention_trend_pct
            col = COLOR_ACCENT_GREEN if ret > 90 else (COLOR_ACCENT_YELLOW if ret > 75 else COLOR_ACCENT_RED)
            self.card_retention.set_value(f"{ret:.1f}%", "Vs baseline retention", color=col)
        else:
            self.card_retention.set_value("Baseline", "Collecting baseline data")

        # Samples
        self.card_samples.set_value(f"{comp.readings_count} pts", f"{comp.data_span_days:.1f} days monitored")

        # Confidence
        conf = comp.confidence.upper()
        if conf == "HIGH":
            badge_color = COLOR_ACCENT_GREEN
            bg_color = "rgba(0, 230, 118, 0.15)"
        elif conf == "MEDIUM":
            badge_color = COLOR_ACCENT_YELLOW
            bg_color = "rgba(255, 214, 0, 0.15)"
        else:
            badge_color = COLOR_TEXT_MUTED
            bg_color = "#222530"

        self.confidence_badge.setText(f"CONFIDENCE: {conf}")
        self.confidence_badge.setStyleSheet(f"""
            background-color: {bg_color};
            color: {badge_color};
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
        """)

        if comp.note:
            self.note_lbl.setText(comp.note)
