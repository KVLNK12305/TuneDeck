"""
Real hardware integration tests for JBL Bluetooth devices.

Safety constraints:
  - Marked @pytest.mark.hardware
  - Excluded by default in pytest.ini (-m "not hardware")
  - Skips unless `--hardware` flag is passed to pytest
  - Skips unless `JBL_BD` environment variable is set
  - Destructive power-off requires `JBLPC_ALLOW_POWEROFF=1` explicitly
    (plus `TUNEDECK_EXPERIMENTAL=1`, since the power-off opcode is unverified)
"""

import os
import pytest
from jblpc.protocol import (
    is_valid_mac,
    check_device_connected,
    BluetoothConnection,
    OP_BATTERY_GET,
    OP_NOISE_GET,
)
from jblpc.controller import HeadsetController


@pytest.fixture
def hardware_target(request):
    """
    Validates safety prerequisites for hardware testing:
      1. --hardware flag present
      2. JBL_BD environment variable defined and valid
    """
    if not request.config.getoption("--hardware"):
        pytest.skip("Hardware tests require explicit --hardware CLI flag.")

    bd_addr = os.environ.get("JBL_BD", "").strip()
    if not bd_addr or not is_valid_mac(bd_addr):
        pytest.skip("Hardware tests require valid JBL_BD environment variable (e.g. AA:BB:CC:DD:EE:FF).")

    if not check_device_connected(bd_addr):
        pytest.skip(f"Device {bd_addr} is not currently connected at the OS Bluetooth level.")

    return bd_addr


@pytest.mark.hardware
def test_hardware_rfcomm_connection(hardware_target):
    """Test establishing real RFCOMM connection to physical hardware."""
    conn = BluetoothConnection(address=hardware_target, channel=21)
    connected = conn.connect(timeout=5.0)
    try:
        assert connected is True, f"Failed to connect to hardware device {hardware_target}: {conn.last_error}"
    finally:
        conn.disconnect()


@pytest.mark.hardware
def test_hardware_battery_query(hardware_target):
    """Test querying real battery level from physical hardware."""
    controller = HeadsetController(bt_address=hardware_target, simulate=False)
    success = controller.connect()
    assert success is True, f"Controller failed to connect: {controller.last_error}"

    level = controller.get_battery()
    # Device should return 0-100% or valid TWS readings
    assert level >= 0 or controller.state.battery_left >= 0, "No battery level reported by hardware."


@pytest.mark.hardware
def test_hardware_safe_poweroff(hardware_target):
    """
    Destructive hardware test: Power off physical device.
    Strictly guarded by JBLPC_ALLOW_POWEROFF=1.
    """
    allow = os.environ.get("TUNEDECK_ALLOW_POWEROFF", os.environ.get("JBLPC_ALLOW_POWEROFF", "")).strip()
    if allow != "1":
        pytest.skip("Destructive power-off requires TUNEDECK_ALLOW_POWEROFF=1 or JBLPC_ALLOW_POWEROFF=1 environment variable.")
    if os.environ.get("TUNEDECK_EXPERIMENTAL", "").strip() != "1":
        pytest.skip("Power-off uses an unverified opcode; set TUNEDECK_EXPERIMENTAL=1 to test it.")

    controller = HeadsetController(bt_address=hardware_target, simulate=False)
    assert controller.connect() is True
    success = controller.power_off()
    assert success is True, f"Failed to send power-off: {controller.last_error}"
