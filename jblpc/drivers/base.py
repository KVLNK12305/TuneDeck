"""
Abstract Base Classes, capabilities, and events for TuneDeck hardware drivers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Flag, auto
import time
from typing import Optional

from ..protocol import NoiseMode, EQPreset


class DriverCapability(Flag):
    """Hardware capability flags for devices and drivers."""
    NONE = 0
    NOISE_ANC = auto()
    NOISE_AMBIENT = auto()
    NOISE_TALKTHRU = auto()
    EQ = auto()
    TWS_TRIO_BATTERY = auto()
    POWER_OFF = auto()
    LIGHTSHOW = auto()
    PARTYBOOST = auto()
    AURACAST = auto()


@dataclass
class DriverEvent:
    """An event emitted by a driver during polling or notification processing."""
    event_type: str  # "noise_mode", "battery", "disconnected", "error"
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class BaseDeviceDriver(ABC):
    """
    Abstract base class for audio device drivers.

    Concrete drivers encapsulate protocol-specific framing, transport sockets,
    and command marshaling for distinct silicon families (Airoha, BES, Qualcomm,
    Actions Semiconductor / JBL Portable).
    """

    def __init__(self, address: str, profile=None):
        self.address = address
        self.profile = profile
        self.last_error: Optional[str] = None

    @property
    @abstractmethod
    def capabilities(self) -> DriverCapability:
        """Return the capabilities supported by this driver for the active model."""
        pass

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Whether the transport socket/session is currently active."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the hardware device."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection and release resources."""
        pass

    @abstractmethod
    def set_noise_mode(self, mode: NoiseMode) -> bool:
        """Set active noise cancellation / ambient mode."""
        pass

    @abstractmethod
    def query_noise_mode(self) -> Optional[NoiseMode]:
        """Query current noise mode from device."""
        pass

    @abstractmethod
    def set_eq_preset(self, preset: EQPreset) -> bool:
        """Set an equalizer preset."""
        pass

    @abstractmethod
    def set_eq_bands(self, bands: list[int]) -> bool:
        """Set custom equalizer band gains."""
        pass

    @abstractmethod
    def get_battery(self) -> Optional[int]:
        """Query current battery percentage."""
        pass

    @abstractmethod
    def poll_events(self) -> list[DriverEvent]:
        """Poll incoming unsolicited telemetry/notifications."""
        pass

    @abstractmethod
    def power_off(self) -> bool:
        """Send remote power-off command."""
        pass

