"""
Custom UI widgets for TuneDeck GUI.
"""

from .battery_gauge import BatteryGaugeWidget
from .noise_control import NoiseControlWidget
from .eq_visualizer import EqualizerWidget
from .health_panel import HealthPanelWidget
from .device_bar import DeviceBarWidget
from .device_spotlight import DeviceSpotlightWidget

__all__ = [
    "BatteryGaugeWidget",
    "NoiseControlWidget",
    "EqualizerWidget",
    "HealthPanelWidget",
    "DeviceBarWidget",
    "DeviceSpotlightWidget",
]
