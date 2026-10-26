"""
TuneDeck GUI Design System and Theme.

Deep onyx dark mode with signature JBL Electric Orange accents (#FF6600),
teal secondary accents, and polished micro-details.
"""

# Brand Colors
COLOR_BG_DARK = "#121316"
COLOR_BG_CARD = "#1A1C23"
COLOR_BG_CARD_ALT = "#20232D"
COLOR_BG_HOVER = "#272B38"
COLOR_BORDER = "#2E3342"
COLOR_BORDER_FOCUS = "#FF6600"

COLOR_JBL_ORANGE = "#FF6600"
COLOR_JBL_ORANGE_HOVER = "#FF7A1A"
COLOR_JBL_ORANGE_ACTIVE = "#E05A00"
COLOR_JBL_ORANGE_DIM = "#4A2200"

COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#9AA0B2"
COLOR_TEXT_MUTED = "#636A7E"

COLOR_ACCENT_CYAN = "#00E5FF"
COLOR_ACCENT_GREEN = "#00E676"
COLOR_ACCENT_YELLOW = "#FFD600"
COLOR_ACCENT_RED = "#FF3D57"

DARK_STYLESHEET = f"""
QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Ubuntu, "Helvetica Neue", sans-serif;
    color: {COLOR_TEXT_PRIMARY};
    background-color: transparent;
}}

/* Must follow the QWidget rule: equal specificity, so the later rule wins */
QMainWindow {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
}}

QScrollArea {{
    border: none;
}}

/* Cards & Containers (widgets set WA_StyledBackground so this paints) */
#cardFrame {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}

QFrame#cardFrameHover:hover {{
    border-color: {COLOR_BORDER_FOCUS};
}}

/* Tab Bar */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}

QTabBar::tab {{
    background: {COLOR_BG_CARD};
    color: {COLOR_TEXT_SECONDARY};
    padding: 10px 24px;
    margin-right: 6px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 13px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background: {COLOR_BG_CARD_ALT};
    color: {COLOR_JBL_ORANGE};
    border-bottom: 3px solid {COLOR_JBL_ORANGE};
}}

QTabBar::tab:hover:!selected {{
    color: {COLOR_TEXT_PRIMARY};
    background: {COLOR_BG_HOVER};
}}

/* Buttons */
QPushButton {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_BORDER_FOCUS};
}}

QPushButton:pressed {{
    background-color: {COLOR_JBL_ORANGE_DIM};
}}

QPushButton#primaryButton {{
    background-color: {COLOR_JBL_ORANGE};
    border: 1px solid {COLOR_JBL_ORANGE};
    color: #FFFFFF;
}}

QPushButton#primaryButton:hover {{
    background-color: {COLOR_JBL_ORANGE_HOVER};
    border-color: {COLOR_JBL_ORANGE_HOVER};
}}

QPushButton#primaryButton:pressed {{
    background-color: {COLOR_JBL_ORANGE_ACTIVE};
}}

QPushButton#dangerButton {{
    background-color: rgba(255, 61, 87, 0.15);
    border: 1px solid {COLOR_ACCENT_RED};
    color: {COLOR_ACCENT_RED};
}}

QPushButton#dangerButton:hover {{
    background-color: {COLOR_ACCENT_RED};
    color: #FFFFFF;
}}

/* Segmented Buttons */
QPushButton#segmentedItem {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 14px;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
}}

QPushButton#segmentedItem:hover {{
    color: {COLOR_TEXT_PRIMARY};
    background-color: {COLOR_BG_HOVER};
}}

QPushButton#segmentedItemSelected {{
    background-color: {COLOR_JBL_ORANGE};
    border: 1px solid {COLOR_JBL_ORANGE};
    color: #FFFFFF;
    font-weight: 700;
}}

QPushButton#segmentedItemDisabled {{
    background-color: {COLOR_BG_DARK};
    border: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_MUTED};
}}

/* Check Box */
QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_TEXT_MUTED};
    border-radius: 4px;
    background-color: {COLOR_BG_CARD};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_JBL_ORANGE};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_JBL_ORANGE};
    border-color: {COLOR_JBL_ORANGE};
}}

/* Combo Box */
QComboBox {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 12px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {COLOR_JBL_ORANGE};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_JBL_ORANGE};
    selection-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    outline: none;
}}

/* Sliders */
QSlider::groove:vertical {{
    background: {COLOR_BG_DARK};
    width: 8px;
    border-radius: 4px;
}}

QSlider::sub-page:vertical {{
    background: {COLOR_BG_DARK};
    border-radius: 4px;
}}

QSlider::add-page:vertical {{
    background: {COLOR_JBL_ORANGE};
    border-radius: 4px;
}}

QSlider::handle:vertical {{
    background: #FFFFFF;
    border: 2px solid {COLOR_JBL_ORANGE};
    height: 18px;
    width: 18px;
    margin: 0 -5px;
    border-radius: 9px;
}}

QSlider::handle:vertical:hover {{
    background: {COLOR_JBL_ORANGE};
    border-color: #FFFFFF;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {COLOR_BG_DARK};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_JBL_ORANGE};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Status Bar & Tooltips */
QStatusBar {{
    background-color: {COLOR_BG_CARD};
    border-top: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}

QToolTip {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    padding: 6px;
    border-radius: 6px;
    font-size: 11px;
}}
"""
