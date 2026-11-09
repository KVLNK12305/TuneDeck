"""
Backend selection facade for Linux Bluetooth discovery.

Auto-selects the best available backend (native D-Bus vs. subprocess fallback)
and exposes a unified interface.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_linux_backend() -> str:
    """Return ``'dbus'`` or ``'subprocess'`` based on runtime availability.

    Prefers the native D-Bus backend when both ``dbus_fast`` is importable
    **and** the BlueZ service is reachable on the system bus. Falls back
    to bluetoothctl subprocess scraping otherwise.
    """
    try:
        from .linux_dbus import DBUS_AVAILABLE
    except ImportError:
        return "subprocess"

    if not DBUS_AVAILABLE:
        return "subprocess"

    try:
        from .linux_dbus import check_dbus_available
        if check_dbus_available():
            return "dbus"
    except Exception as exc:
        logger.debug("D-Bus availability check failed: %s", exc)

    return "subprocess"


def find_jbl_devices_linux() -> list[dict]:
    """Find JBL devices on Linux using D-Bus if available, or subprocess fallback."""
    backend = get_linux_backend()
    if backend == "dbus":
        try:
            from .linux_dbus import find_jbl_devices_dbus
            return find_jbl_devices_dbus()
        except Exception as exc:
            logger.debug("D-Bus discovery failed, falling back to subprocess: %s", exc)

    from .bluez_subprocess import find_jbl_devices_subprocess
    return find_jbl_devices_subprocess()


def get_battery_level_linux(address: str) -> Optional[int]:
    """Get battery percentage on Linux using D-Bus if available, or subprocess fallback."""
    backend = get_linux_backend()
    if backend == "dbus":
        try:
            from .linux_dbus import get_battery_level_dbus
            val = get_battery_level_dbus(address)
            if val is not None:
                return val
        except Exception as exc:
            logger.debug("D-Bus battery query failed, falling back to subprocess: %s", exc)

    from .bluez_subprocess import get_system_battery_level_subprocess
    return get_system_battery_level_subprocess(address)


def check_device_connected_linux(address: str) -> bool:
    """Check if device is connected using subprocess fallback."""
    from .bluez_subprocess import check_device_connected_subprocess
    return check_device_connected_subprocess(address)


def check_device_paired_linux(address: str) -> bool:
    """Check if device is paired using subprocess fallback."""
    from .bluez_subprocess import check_device_paired_subprocess
    return check_device_paired_subprocess(address)


def check_bluetooth_adapter_powered_linux() -> None:
    """Check if adapter is powered using subprocess fallback."""
    from .bluez_subprocess import check_bluetooth_adapter_powered_subprocess
    check_bluetooth_adapter_powered_subprocess()
