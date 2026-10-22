"""
Device Spotlight Widget — Displays high-fidelity product imagery and hardware specs.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPainterPath,
    QColor,
    QPen,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)

from jblpc.models import DeviceProfile, DeviceCategory
from ..theme import (
    COLOR_BG_DARK,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
    COLOR_JBL_ORANGE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "devices"


def get_device_image_path(profile: DeviceProfile) -> Path:
    """Return the product image path matching the model or category."""
    # 1. Exact model id image
    model_img = ASSETS_DIR / f"{profile.model_id}.jpg"
    if model_img.exists():
        return model_img

    # 2. Family match
    mid = profile.model_id.lower()
    name = profile.display_name.lower()

    if profile.category == DeviceCategory.PARTYBOX or "partybox" in mid or "partybox" in name:
        return ASSETS_DIR / "partybox.jpg"
    elif profile.category == DeviceCategory.SPEAKER or "flip" in mid or "charge" in mid or "xtreme" in mid or "boombox" in mid or "pulse" in mid:
        return ASSETS_DIR / "speaker.jpg"
    elif profile.category == DeviceCategory.TWS or "tws" in mid or "buds" in mid or "beam" in mid or "flex" in mid:
        return ASSETS_DIR / "tws.jpg"
    else:
        return ASSETS_DIR / "headphones.jpg"


class DeviceSpotlightWidget(QWidget):
    """
    Displays the actual hardware product picture, category badge,
    and capability tags for the currently selected JBL model.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setFixedWidth(270)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header Title
        title_box = QHBoxLayout()
        header_lbl = QLabel("DEVICE SPOTLIGHT")
        header_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        title_box.addWidget(header_lbl)
        title_box.addStretch()

        self.protocol_tag = QLabel("AIROHA RACE")
        self.protocol_tag.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {COLOR_JBL_ORANGE};
            background-color: rgba(255, 102, 0, 0.12);
            padding: 2px 6px;
            border-radius: 4px;
        """)
        title_box.addWidget(self.protocol_tag)
        layout.addLayout(title_box)

        # Product Image Frame
        self.img_frame = QLabel()
        self.img_frame.setFixedHeight(180)
        self.img_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_frame.setStyleSheet(f"""
            QLabel {{
                background-color: {COLOR_BG_DARK};
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
            }}
        """)
        layout.addWidget(self.img_frame)

        # Device Model Title
        self.name_lbl = QLabel("JBL Tune 770NC")
        self.name_lbl.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        self.name_lbl.setWordWrap(True)
        layout.addWidget(self.name_lbl)

        # Category subtitle
        self.cat_lbl = QLabel("Over-Ear Headphones")
        self.cat_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(self.cat_lbl)

        # Feature pills container with pre-allocated labels
        self.features_layout = QHBoxLayout()
        self.features_layout.setSpacing(4)
        layout.addLayout(self.features_layout)

        self.tag_labels: list[QLabel] = []
        for _ in range(4):
            lbl = QLabel()
            lbl.setStyleSheet(f"""
                font-size: 10px;
                font-weight: 600;
                color: {COLOR_TEXT_SECONDARY};
                background-color: {COLOR_BG_CARD_ALT};
                border: 1px solid {COLOR_BORDER};
                padding: 3px 6px;
                border-radius: 4px;
            """)
            lbl.hide()
            self.features_layout.addWidget(lbl)
            self.tag_labels.append(lbl)

        self.features_layout.addStretch()
        layout.addStretch()

    def update_from_state(self, state):
        """Update product image, model details, and hardware feature tags."""
        profile = state.profile
        self.name_lbl.setText(profile.display_name)
        self.cat_lbl.setText(profile.category.value)
        self.protocol_tag.setText(profile.protocol_family.value.upper())

        # Load and render device product image with rounded corners
        img_path = get_device_image_path(profile)
        if img_path.exists():
            pix = QPixmap(str(img_path))
            scaled = pix.scaled(
                238, 178,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            # Mask with rounded corners
            rounded = QPixmap(238, 178)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            path = QPainterPath()
            path.addRoundedRect(0, 0, 238, 178, 10, 10)
            painter.setClipPath(path)
            # Center cropped
            offset_x = (scaled.width() - 238) // 2
            offset_y = (scaled.height() - 178) // 2
            painter.drawPixmap(0, 0, scaled, offset_x, offset_y, 238, 178)
            painter.end()

            self.img_frame.setPixmap(rounded)
        else:
            self.img_frame.clear()
            self.img_frame.setText("No Image Available")

        # Update static feature tags
        tags = []
        if profile.has_anc:
            tags.append("ANC")
        if profile.has_ambient_aware:
            tags.append("Ambient")
        if profile.has_talkthru:
            tags.append("TalkThru")
        if len(profile.eq_band_frequencies) > 0:
            tags.append(f"{len(profile.eq_band_frequencies)}-Band EQ")
        if profile.has_partyboost:
            tags.append("PartyBoost")
        if profile.has_auracast:
            tags.append("Auracast")

        for i, lbl in enumerate(self.tag_labels):
            if i < len(tags):
                lbl.setText(tags[i])
                lbl.show()
            else:
                lbl.hide()
