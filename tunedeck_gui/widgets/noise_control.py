"""
Noise Control Mode Selector Widget (ANC, Ambient Aware, TalkThru, Off).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from jblpc.protocol import NoiseMode
from ..theme import (
    COLOR_BORDER,
    COLOR_JBL_ORANGE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)


class NoiseControlWidget(QWidget):
    """
    Segmented noise control selector with capability gating per model.
    """
    mode_changed = Signal(object)  # NoiseMode

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(12)

        # Header Title
        title_box = QHBoxLayout()
        title_lbl = QLabel("ACTIVE NOISE CONTROL")
        title_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self.active_mode_lbl = QLabel("Off")
        self.active_mode_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLOR_JBL_ORANGE};")
        title_box.addWidget(self.active_mode_lbl)
        self._layout.addLayout(title_box)

        # Button Group Container
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        self._layout.addLayout(btn_box)

        self.buttons: dict[NoiseMode, QPushButton] = {}

        modes = [
            (NoiseMode.ANC, "ANC", "Active Noise Cancellation"),
            (NoiseMode.AMBIENT_AWARE, "Ambient", "Ambient Aware pass-through"),
            (NoiseMode.TALKTHRU, "TalkThru", "TalkThru speech amplification"),
            (NoiseMode.OFF, "Off", "Disable Noise Processing"),
        ]

        for mode, label, tooltip in modes:
            btn = QPushButton(label)
            btn.setObjectName("segmentedItem")
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, m=mode: self._on_btn_clicked(m))
            btn_box.addWidget(btn)
            self.buttons[mode] = btn

        self._current_mode = NoiseMode.OFF

    def _on_btn_clicked(self, mode: NoiseMode):
        self.mode_changed.emit(mode)

    def update_from_state(self, state):
        """Update button selection and capability gating based on state and profile."""
        profile = state.profile
        self._current_mode = state.noise_mode
        self.active_mode_lbl.setText(state.noise_mode_name)

        # Models such as Wave Buds have Ambient/TalkThru without ANC, so gate on
        # any noise capability; with none, hide the whole card.
        if not (profile.has_anc or profile.has_ambient_aware or profile.has_talkthru):
            for btn in self.buttons.values():
                btn.setVisible(False)
                btn.setEnabled(False)
            self.hide()
            return
        self.show()

        # Capability checks: only show supported options
        capabilities = {
            NoiseMode.ANC: profile.has_anc,
            NoiseMode.AMBIENT_AWARE: profile.has_ambient_aware,
            NoiseMode.TALKTHRU: profile.has_talkthru,
            NoiseMode.OFF: True,
        }

        for mode, btn in self.buttons.items():
            supported = capabilities.get(mode, False)
            btn.setVisible(supported)
            btn.setEnabled(supported)

            if not supported:
                btn.setObjectName("segmentedItemDisabled")
                btn.setToolTip(f"{mode.name} is not supported by {profile.display_name}")
            elif mode == self._current_mode:
                btn.setObjectName("segmentedItemSelected")
            else:
                btn.setObjectName("segmentedItem")

            # Force re-polish stylesheet
            btn.style().unpolish(btn)
            btn.style().polish(btn)
