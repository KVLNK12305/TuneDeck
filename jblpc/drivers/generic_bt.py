"""
Generic Bluetooth driver for standard headsets and uncataloged devices.

Relies strictly on standard OS Bluetooth profiles (HFP, AVRCP, BLE Battery Service)
for battery reporting, and disallows proprietary vendor command sets.
"""

from typing import Optional

from .base import BaseDeviceDriver, DriverCapability, DriverEvent
from ..protocol import NoiseMode, EQPreset, get_system_battery_level, check_device_connected
from ..exceptions import UnsupportedCommandError


class GenericBtDriver(BaseDeviceDriver):
    """Fallback driver for generic Bluetooth audio devices without vendor extensions."""

    @property
    def capabilities(self) -> DriverCapability:
        return DriverCapability.NONE

    @property
    def connected(self) -> bool:
        if not self.address:
            return False
        return check_device_connected(self.address)

    def connect(self) -> bool:
        if not self.address:
            self.last_error = "No device address specified."
            return False
        if not check_device_connected(self.address):
            self.last_error = f"Device {self.address} is not connected at OS level."
            return False
        return True

    def disconnect(self) -> None:
        pass

    def set_noise_mode(self, mode: NoiseMode) -> bool:
        raise UnsupportedCommandError("Generic Bluetooth devices do not support proprietary noise control.")

    def query_noise_mode(self) -> Optional[NoiseMode]:
        return None

    def set_eq_preset(self, preset: EQPreset) -> bool:
        raise UnsupportedCommandError("Generic Bluetooth devices do not support hardware EQ commands.")

    def set_eq_bands(self, bands: list[int]) -> bool:
        raise UnsupportedCommandError("Generic Bluetooth devices do not support hardware EQ commands.")

    def get_battery(self) -> Optional[int]:
        if self.address:
            return get_system_battery_level(self.address)
        return None

    def poll_events(self) -> list[DriverEvent]:
        return []

    def power_off(self) -> bool:
        raise UnsupportedCommandError("Generic Bluetooth devices do not support remote power-off.")

