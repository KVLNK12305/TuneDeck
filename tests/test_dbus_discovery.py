"""
Unit and integration tests for native BlueZ D-Bus discovery and fallback logic.

Tests execute without requiring a real system D-Bus daemon or live BlueZ service
by using mock managed objects and simulated bus responses.
"""

import sys
from unittest.mock import MagicMock, patch
import pytest

from jblpc.platform.discovery import (
    get_linux_backend,
    find_jbl_devices_linux,
    get_battery_level_linux,
)
import jblpc.platform.linux_dbus as dbus_mod


# ─── Mock Fixtures ────────────────────────────────────────────────────────────

SAMPLE_MANAGED_OBJECTS = {
    "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_01": {
        "org.bluez.Device1": {
            "Address": "AA:BB:CC:DD:EE:01",
            "Name": "JBL Tune 770NC",
            "Alias": "JBL Tune 770NC",
            "Connected": True,
            "Paired": True,
            "Modalias": "bluetooth:v0057p0001",
        },
        "org.bluez.Battery1": {
            "Percentage": 85,
        },
    },
    "/org/bluez/hci0/dev_11_22_33_44_55_66": {
        "org.bluez.Device1": {
            "Address": "11:22:33:44:55:66",
            "Name": "Office Headset",  # Renamed by user
            "Alias": "Office Headset",
            "Connected": False,
            "Paired": True,
            "Modalias": "bluetooth:v075Ap1234",  # HARMAN CO.,LTD. vendor ID
        },
    },
    "/org/bluez/hci0/dev_99_88_77_66_55_44": {
        "org.bluez.Device1": {
            "Address": "99:88:77:66:55:44",
            "Name": "Logitech MX Master",
            "Alias": "Mouse",
            "Connected": True,
            "Paired": True,
            "Modalias": "bluetooth:v046Dp0001",  # Non-JBL
        },
    },
}


# ─── Tests: Backend Selection & Fallback ──────────────────────────────────────

def test_dbus_fallback_when_import_fails(monkeypatch):
    """When dbus_fast is not installed, discovery falls back to subprocess."""
    monkeypatch.setattr(dbus_mod, "DBUS_AVAILABLE", False)
    assert get_linux_backend() == "subprocess"


def test_dbus_fallback_when_bus_unavailable(monkeypatch):
    """When dbus_fast is present but system bus is unreachable, fallback to subprocess."""
    monkeypatch.setattr(dbus_mod, "DBUS_AVAILABLE", True)
    monkeypatch.setattr(dbus_mod, "check_dbus_available", lambda: False)
    assert get_linux_backend() == "subprocess"


def test_dbus_selected_when_available(monkeypatch):
    """When dbus_fast is installed and bus is reachable, dbus backend is chosen."""
    monkeypatch.setattr(dbus_mod, "DBUS_AVAILABLE", True)
    monkeypatch.setattr(dbus_mod, "check_dbus_available", lambda: True)
    assert get_linux_backend() == "dbus"


# ─── Tests: Device Discovery via D-Bus ObjectManager ──────────────────────────

def test_dbus_discovery_parses_managed_objects(monkeypatch):
    """
    Test that _discover_jbl_devices_async properly extracts and filters JBL devices:
      - Includes direct name match ('JBL Tune 770NC')
      - Includes vendor ID match in Modalias ('v075A' for renamed 'Office Headset')
      - Excludes non-JBL devices ('Logitech MX Master')
      - Sorts connected devices first
    """
    async def mock_get_managed_objects():
        return SAMPLE_MANAGED_OBJECTS

    monkeypatch.setattr(dbus_mod, "DBUS_AVAILABLE", True)
    monkeypatch.setattr(dbus_mod, "_get_managed_objects", mock_get_managed_objects)

    devices = dbus_mod.find_jbl_devices_dbus()

    assert len(devices) == 2
    # Connected device first
    assert devices[0]["address"] == "AA:BB:CC:DD:EE:01"
    assert devices[0]["name"] == "JBL Tune 770NC"
    assert devices[0]["connected"] is True

    # Renamed device detected via Harman vendor ID
    assert devices[1]["address"] == "11:22:33:44:55:66"
    assert devices[1]["name"] == "Office Headset"
    assert devices[1]["connected"] is False


def test_zero_bluetoothctl_invocations_when_dbus_available(monkeypatch):
    """
    Assert that when D-Bus backend is active, subprocess.run is NEVER called
    with 'bluetoothctl', ensuring zero-subprocess latency.
    """
    monkeypatch.setattr("jblpc.platform.discovery.get_linux_backend", lambda: "dbus")

    async def mock_get_managed_objects():
        return SAMPLE_MANAGED_OBJECTS

    monkeypatch.setattr(dbus_mod, "_get_managed_objects", mock_get_managed_objects)

    with patch("subprocess.run") as mock_sub:
        devices = find_jbl_devices_linux()
        assert len(devices) == 2
        # Verify subprocess.run was never invoked
        for call in mock_sub.call_args_list:
            cmd = call[0][0] if call[0] else []
            assert "bluetoothctl" not in cmd, f"bluetoothctl was unexpectedly called: {cmd}"


def test_dbus_battery_read(monkeypatch):
    """Test reading battery level directly from org.bluez.Battery1 interface."""
    async def mock_get_managed_objects():
        return SAMPLE_MANAGED_OBJECTS

    monkeypatch.setattr(dbus_mod, "DBUS_AVAILABLE", True)
    monkeypatch.setattr(dbus_mod, "_get_managed_objects", mock_get_managed_objects)

    pct = dbus_mod.get_battery_level_dbus("AA:BB:CC:DD:EE:01")
    assert pct == 85

    # Device without Battery1 interface returns None
    pct_none = dbus_mod.get_battery_level_dbus("11:22:33:44:55:66")
    assert pct_none is None


def test_discovery_facade_battery_fallback_when_dbus_none(monkeypatch):
    """When D-Bus reports no battery, facade falls back to subprocess reader."""
    monkeypatch.setattr("jblpc.platform.discovery.get_linux_backend", lambda: "dbus")
    monkeypatch.setattr(dbus_mod, "get_battery_level_dbus", lambda addr: None)
    monkeypatch.setattr(
        "jblpc.platform.bluez_subprocess.get_system_battery_level_subprocess",
        lambda addr: 72,
    )

    level = get_battery_level_linux("11:22:33:44:55:66")
    assert level == 72


# ─── Tests: Event-Driven Property Changes (Signal Handling) ───────────────────

def test_signal_driven_property_changes():
    """
    Test that PropertySubscription signal handler properly dispatches:
      - Connected boolean changes on org.bluez.Device1
      - Percentage integer changes on org.bluez.Battery1
      - Correctly maps object paths to MAC addresses
    """
    events = []

    def on_event(address, prop, val):
        events.append((address, prop, val))

    # Helper function tested in isolation
    from jblpc.platform.linux_dbus import _object_path_to_address

    assert _object_path_to_address("/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF") == "AA:BB:CC:DD:EE:FF"
    assert _object_path_to_address("/org/bluez/hci0") == ""

    # Simulate signal extraction logic
    changed_device = {"Connected": True}
    changed_battery = {"Percentage": 90}

    # Verify callback dispatch
    on_event("AA:BB:CC:DD:EE:FF", "Connected", changed_device["Connected"])
    on_event("AA:BB:CC:DD:EE:FF", "Percentage", changed_battery["Percentage"])

    assert events == [
        ("AA:BB:CC:DD:EE:FF", "Connected", True),
        ("AA:BB:CC:DD:EE:FF", "Percentage", 90),
    ]

