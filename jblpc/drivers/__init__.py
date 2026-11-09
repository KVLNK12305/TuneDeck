"""
TuneDeck hardware device driver package.

Exposes pluggable drivers for different silicon and protocol families:
- AirohaRaceDriver: Airoha AB156x / AB158x headphones and TWS over RFCOMM 21
- JblPortableDriver: Flip, Charge, Xtreme, Boombox, PartyBox over SPP/BLE (stub)
- GenericBtDriver: Standard OS Bluetooth devices without vendor extensions
"""

from typing import Optional

from .base import BaseDeviceDriver, DriverCapability, DriverEvent
from .airoha_race import AirohaRaceDriver
from .jbl_portable import JblPortableDriver
from .generic_bt import GenericBtDriver
from ..models import ProtocolFamily, DeviceProfile


def get_driver_for_profile(
    address: str,
    profile: Optional[DeviceProfile] = None,
    connection=None,
) -> BaseDeviceDriver:
    """Factory function: select the appropriate driver for a device profile."""
    family = profile.protocol_family if profile else ProtocolFamily.AIROHA_RACE

    if family == ProtocolFamily.AIROHA_RACE:
        return AirohaRaceDriver(address, profile=profile, connection=connection)
    elif family in (ProtocolFamily.JBL_PORTABLE, ProtocolFamily.PARTYBOX):
        return JblPortableDriver(address, profile=profile)
    elif family == ProtocolFamily.GENERIC_BT:
        return GenericBtDriver(address, profile=profile)
    else:
        # Default fallback
        return AirohaRaceDriver(address, profile=profile, connection=connection)


__all__ = [
    "BaseDeviceDriver",
    "DriverCapability",
    "DriverEvent",
    "AirohaRaceDriver",
    "JblPortableDriver",
    "GenericBtDriver",
    "get_driver_for_profile",
]

