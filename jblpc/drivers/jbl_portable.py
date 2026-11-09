"""
Stub driver for JBL Portable (Flip, Charge, Xtreme, Boombox) and PartyBox speakers.

These devices use Harman's proprietary SPP / BLE protocol (formerly JBL Connect /
PartyBoost / Auracast) rather than Airoha RACE. Hardware control is not yet
implemented and is blocked on protocol reverse-engineering (APK research).
"""

from typing import Optional

from .base import BaseDeviceDriver, DriverCapability, DriverEvent
from ..protocol import NoiseMode, EQPreset, get_system_battery_level
from ..exceptions import UnsupportedCommandError


class JblPortableDriver(BaseDeviceDriver):
    """
    Driver stub for JBL Portable and PartyBox protocol family.

    Currently refuses hardware operations with an informative UnsupportedCommandError
    and guides the user to use simulation mode (--sim).
    """

    @property
    def capabilities(self) -> DriverCapability:
        caps = DriverCapability.NONE
        if self.profile and self.profile.has_partyboost:
            caps |= DriverCapability.PARTYBOOST
        if self.profile and self.profile.has_auracast:
            caps |= DriverCapability.AURACAST
        if self.profile and self.profile.has_lightshow:
            caps |= DriverCapability.LIGHTSHOW
        return caps

    @property
    def connected(self) -> bool:
        return False

    def connect(self) -> bool:
        model_name = self.profile.display_name if self.profile else "JBL Portable Speaker"
        family_val = self.profile.protocol_family.value if self.profile else "JBL Portable / PartyBoost"
        self.last_error = (
            f"Hardware control for {model_name} "
            f"({family_val}) is not implemented; "
            f"only Airoha RACE headphones and earbuds are supported. Use --sim to explore the UI."
        )
        return False

    def disconnect(self) -> None:
        pass

    def set_noise_mode(self, mode: NoiseMode) -> bool:
        raise UnsupportedCommandError("Portable speakers and PartyBoxes do not support noise control.")

    def query_noise_mode(self) -> Optional[NoiseMode]:
        return None

    def set_eq_preset(self, preset: EQPreset) -> bool:
        raise UnsupportedCommandError(
            "Hardware EQ for JBL Portable speakers is not yet implemented (blocked on protocol research)."
        )

    def set_eq_bands(self, bands: list[int]) -> bool:
        raise UnsupportedCommandError(
            "Hardware EQ for JBL Portable speakers is not yet implemented (blocked on protocol research)."
        )

    def get_battery(self) -> Optional[int]:
        if self.address:
            return get_system_battery_level(self.address)
        return None

    def poll_events(self) -> list[DriverEvent]:
        return []

    def power_off(self) -> bool:
        raise UnsupportedCommandError("Remote power-off is not supported over BLE for portable speakers.")

