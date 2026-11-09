"""
Airoha RACE protocol driver for JBL Tune/Live series headphones and earbuds.

Communicates over RFCOMM channel 21 using Airoha RACE frame encapsulation:
[0x05, 0x5A/0x5B/0x5C, Length (2B LE), Opcode (2B LE), Payload]
"""

import os
from typing import Optional

from .base import BaseDeviceDriver, DriverCapability, DriverEvent
from ..protocol import (
    BluetoothConnection,
    NoiseMode,
    EQPreset,
    NOISE_SETTERS,
    OP_NOISE_SET,
    OP_NOISE_GET,
    OP_NOISE_GET_PAYLOAD,
    OP_BATTERY_PERCENTAGE,
    OP_BATTERY_GET,
    OP_POWER_OFF,
    OP_EQ_SET,
    get_system_battery_level,
)
from ..exceptions import UnsupportedCommandError


def _experimental_enabled() -> bool:
    return os.environ.get("TUNEDECK_EXPERIMENTAL", "").strip() == "1"


class AirohaRaceDriver(BaseDeviceDriver):
    """Driver implementation for Airoha RACE protocol over RFCOMM."""

    def __init__(self, address: str, profile=None, connection: Optional[BluetoothConnection] = None):
        super().__init__(address, profile)
        channel = profile.rfcomm_channel if profile else 21
        self._connection = connection or BluetoothConnection(address, channel=channel)

    @property
    def capabilities(self) -> DriverCapability:
        caps = DriverCapability.NOISE_ANC | DriverCapability.NOISE_AMBIENT | DriverCapability.NOISE_TALKTHRU
        if self.profile and self.profile.has_power_off_command:
            caps |= DriverCapability.POWER_OFF
        caps |= DriverCapability.EQ
        return caps

    @property
    def connected(self) -> bool:
        return self._connection.connected

    def connect(self) -> bool:
        self.last_error = None
        success = self._connection.connect()
        if not success:
            self.last_error = self._connection.last_error
        return success

    def disconnect(self) -> None:
        self._connection.disconnect()

    def set_noise_mode(self, mode: NoiseMode) -> bool:
        self.last_error = None
        if not self.connected:
            self.last_error = "Device is not connected."
            return False

        payload = NOISE_SETTERS.get(mode)
        if payload is None:
            self.last_error = f"Unsupported noise mode: {mode}"
            return False

        success = self._connection.send_command(OP_NOISE_SET, payload)
        if not success:
            self.last_error = self._connection.last_error or "Failed to send noise command."
            return False

        # Drain confirmation frames
        frames = self._connection.receive(timeout=1.5)
        for frame in frames:
            if frame.noise_mode is not None:
                return True
        return success

    def query_noise_mode(self) -> Optional[NoiseMode]:
        if not self.connected:
            return None
        frames = self._connection.send_and_receive(
            OP_NOISE_GET, payload=OP_NOISE_GET_PAYLOAD, timeout=2.0
        )
        for frame in frames:
            if frame.noise_mode is not None:
                return frame.noise_mode
        return None

    def set_eq_preset(self, preset: EQPreset) -> bool:
        self.last_error = None
        if not self.connected:
            self.last_error = "Device is not connected."
            return False
        if not _experimental_enabled():
            self.last_error = "EQ on hardware is experimental (set TUNEDECK_EXPERIMENTAL=1)."
            return False

        payload = bytes([int(preset.value)])
        success = self._connection.send_command(OP_EQ_SET, payload)
        if not success:
            self.last_error = self._connection.last_error or "Failed to send EQ preset."
        return success

    def set_eq_bands(self, bands: list[int]) -> bool:
        self.last_error = None
        if not self.connected:
            self.last_error = "Device is not connected."
            return False
        if not _experimental_enabled():
            self.last_error = "EQ on hardware is experimental (set TUNEDECK_EXPERIMENTAL=1)."
            return False

        clamped = [max(-12, min(12, int(b))) for b in bands]
        payload = bytes([len(clamped)] + [b & 0xFF for b in clamped])
        success = self._connection.send_command(OP_EQ_SET, payload)
        if not success:
            self.last_error = self._connection.last_error or "Failed to send EQ bands."
        return success

    def get_battery(self) -> Optional[int]:
        # 1. Query OS Bluetooth stack first (most reliable)
        if self.address:
            sys_level = get_system_battery_level(self.address)
            if sys_level is not None and 0 <= sys_level <= 100:
                return sys_level

        # 2. Fallback to RFCOMM telemetry
        if not self.connected:
            return None

        frames = self._connection.send_and_receive(OP_BATTERY_PERCENTAGE, timeout=1.0)
        for frame in frames:
            if frame.battery_level is not None:
                return frame.battery_level

        frames = self._connection.send_and_receive(OP_BATTERY_GET, timeout=1.0)
        for frame in frames:
            if frame.battery_level is not None and frame.battery_level > 10:
                return frame.battery_level
        return None

    def poll_events(self) -> list[DriverEvent]:
        events = []
        if not self.connected:
            return events

        try:
            frames = self._connection.receive(timeout=0.05)
            for f in frames:
                if f.noise_mode is not None:
                    events.append(DriverEvent("noise_mode", {"mode": f.noise_mode}))
                if f.battery_level is not None:
                    events.append(DriverEvent("battery", {"level": f.battery_level}))
        except Exception:
            pass
        return events

    def power_off(self) -> bool:
        self.last_error = None
        if not self.connected:
            self.last_error = "Device is not connected."
            return False
        if not _experimental_enabled():
            self.last_error = "Power off is experimental (set TUNEDECK_EXPERIMENTAL=1)."
            return False

        success = self._connection.send_command(OP_POWER_OFF)
        if success:
            self.disconnect()
        else:
            self.last_error = self._connection.last_error or "Failed to send power off command."
        return success

