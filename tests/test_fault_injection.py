"""
Fault injection tests simulating hardware, system, network, and protocol failures.
Validates that:
  - No raw tracebacks are displayed
  - Clear one-line error messages are returned
  - Non-zero exit codes in CLI mode
  - Resources (sockets, locks) are closed cleanly
  - No hanging beyond timeout
"""

import os
import sys
import json
import signal
import socket
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from jblpc.protocol import (
    load_config,
    save_config,
    parse_frames,
    build_request,
    check_bluetooth_adapter_powered,
    check_bluetoothctl_available,
    check_device_paired,
    find_jbl_devices,
    BluetoothConnection,
    OP_NOISE_SET,
    OP_NOISE_GET,
    OP_BATTERY_GET,
    OP_POWER_OFF,
    MAGIC_BYTE,
)
from jblpc.controller import HeadsetController
from jblpc.exceptions import (
    JBLPcError,
    ConfigError,
    BluetoothAdapterError,
    DeviceNotPairedError,
    JBLConnectionError,
    ProtocolError,
    UnsupportedCommandError,
    InstanceLockError,
)
from jblpc.lock import SingleInstanceLock
from jblpc.cli import run_cli
from tests.conftest import FakeRFCOMMSocket, FakeBluetoothConnection


# 1. Bluetooth adapter off or missing
@pytest.mark.fault
def test_fault_bluetooth_adapter_off(isolated_env):
    """Simulate Bluetooth adapter powered off."""
    mock_res = MagicMock()
    mock_res.stdout = b"Controller AA:BB:CC:DD:EE:FF\n\tPowered: no\n"
    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(BluetoothAdapterError) as exc_info:
            check_bluetooth_adapter_powered()
        assert "powered off or missing" in str(exc_info.value)

        # CLI execution
        ret = run_cli(["status"])
        assert ret == 1


# 2. bluetoothctl not installed
@pytest.mark.fault
def test_fault_bluetoothctl_not_installed(isolated_env):
    """Simulate bluetoothctl missing from PATH."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(BluetoothAdapterError) as exc_info:
            check_bluetoothctl_available()
        assert "bluetoothctl utility is not installed" in str(exc_info.value)

        ret = run_cli(["scan"])
        assert ret == 1


# 3. Device not paired
@pytest.mark.fault
def test_fault_device_not_paired(isolated_env):
    """Simulate device not paired in bluetoothctl."""
    mock_res = MagicMock()
    mock_res.stdout = b"Device 11:22:33:44:55:66\n\tPaired: no\n"
    with patch("subprocess.run", return_value=mock_res):
        paired = check_device_paired("11:22:33:44:55:66")
        assert paired is False

        controller = HeadsetController(bt_address="11:22:33:44:55:66", simulate=False)
        success = controller.connect()
        assert success is False
        assert "not paired" in controller.last_error


# 4. Invalid or missing MAC address
@pytest.mark.fault
def test_fault_invalid_or_missing_mac(isolated_env):
    """Simulate missing or invalid MAC address."""
    # Missing MAC
    controller_empty = HeadsetController(bt_address="", simulate=False)
    assert controller_empty.connect() is False
    assert "No JBL device found" in controller_empty.last_error

    # Invalid MAC
    controller_inv = HeadsetController(bt_address="invalid_mac", simulate=False)
    assert controller_inv.connect() is False
    assert "Invalid Bluetooth MAC address" in controller_inv.last_error


# 5. Corrupt or empty config.json
@pytest.mark.fault
def test_fault_corrupt_or_empty_config(isolated_env):
    """Simulate empty or malformed config.json."""
    config_file = isolated_env["config_dir"] / "jblpc" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Empty config
    config_file.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError) as exc_info:
        load_config()
    assert "is empty" in str(exc_info.value)

    # Corrupt JSON config
    config_file.write_text("{corrupt: true,", encoding="utf-8")
    with pytest.raises(ConfigError) as exc_info:
        load_config()
    assert "Corrupt configuration" in str(exc_info.value)


# 6. Missing config dir
@pytest.mark.fault
def test_fault_missing_config_dir(isolated_env):
    """Simulate missing config dir; should return default config and auto-create on save."""
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert cfg["rfcomm_channel"] == 21

    cfg["test_key"] = "test_val"
    save_config(cfg)
    saved = load_config()
    assert saved["test_key"] == "test_val"


# 7. Connection refused
@pytest.mark.fault
def test_fault_connection_refused(isolated_env):
    """Simulate connection refused by RFCOMM channel."""
    fake_sock = FakeRFCOMMSocket(fail_on_connect=ConnectionRefusedError("Connection refused"))
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    assert conn.connect() is False
    assert "Connection refused" in conn.last_error
    assert not conn.connected


# 8. Connect timeout
@pytest.mark.fault
def test_fault_connect_timeout(isolated_env):
    """Simulate RFCOMM connect timeout."""
    fake_sock = FakeRFCOMMSocket(fail_on_connect=TimeoutError("Connection timed out"))
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    assert conn.connect() is False
    assert "Connection timeout" in conn.last_error
    assert not conn.connected


# 9. Read timeout
@pytest.mark.fault
def test_fault_read_timeout(isolated_env):
    """Simulate socket read timeout during frame reception."""
    fake_sock = FakeRFCOMMSocket(fail_on_recv=socket.timeout("The read operation timed out"))
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    conn._sock = fake_sock
    frames = conn.receive(timeout=0.1)
    assert frames == []


# 10. Disconnect mid-command
@pytest.mark.fault
def test_fault_disconnect_mid_command(isolated_env):
    """Simulate remote device disconnecting (EOF / 0 bytes received) mid-command."""
    fake_sock = FakeRFCOMMSocket(disconnect_mid_read=True)
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    conn._sock = fake_sock
    frames = conn.receive(timeout=1.0)
    assert frames == []
    assert "disconnected unexpectedly" in conn.last_error
    assert not conn.connected


# 11. Partial frame
@pytest.mark.fault
def test_fault_partial_frame(isolated_env):
    """Simulate partial frame bytes; parser must not crash and buffer remainder."""
    full_frame = build_request(OP_BATTERY_GET)
    partial = full_frame[:5]
    frames, rem = parse_frames(partial)
    assert len(frames) == 0
    assert rem == partial


# 12. Unverified command on hardware
@pytest.mark.fault
def test_fault_unverified_command_blocked(isolated_env, monkeypatch):
    """EQ and power-off use unverified opcodes; nothing is sent unless TUNEDECK_EXPERIMENTAL=1."""
    from jblpc.protocol import EQPreset

    monkeypatch.delenv("TUNEDECK_EXPERIMENTAL", raising=False)
    fake_sock = FakeRFCOMMSocket()
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    controller = HeadsetController(bt_address="", model_id="tune_770nc", connection=conn)
    assert conn.connect() is True
    controller.state.connected = True

    assert controller.set_eq_preset(EQPreset.BASS) is False
    assert "TUNEDECK_EXPERIMENTAL" in controller.last_error
    assert controller.set_eq_bands([0] * 10) is False
    assert controller.power_off() is False
    assert "TUNEDECK_EXPERIMENTAL" in controller.last_error
    assert fake_sock.sent_data == []

    monkeypatch.setenv("TUNEDECK_EXPERIMENTAL", "1")
    assert controller.set_eq_preset(EQPreset.BASS) is True
    assert len(fake_sock.sent_data) == 1


# 13. Unexpected response opcode
@pytest.mark.fault
def test_fault_unexpected_response_opcode(isolated_env):
    """Simulate device returning an unexpected opcode for a requested command."""
    # Respond with OP_NOISE_SET when OP_BATTERY_GET was requested
    resp_frame = build_request(OP_NOISE_SET)
    fake_sock = FakeRFCOMMSocket(response_queue=[resp_frame])
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    assert conn.connect() is True
    with pytest.raises(ProtocolError) as exc_info:
        conn.send_and_receive(OP_BATTERY_GET, expect_opcode=OP_BATTERY_GET)
    assert "Unexpected response opcode" in str(exc_info.value)


# 14. Command unsupported by the model
@pytest.mark.fault
def test_fault_command_unsupported_by_model(isolated_env):
    """Simulate executing commands not supported by specific hardware models."""
    # ANC on Flip 6 speaker
    controller_flip = HeadsetController(simulate=True, model_id="flip_6")
    from jblpc.protocol import NoiseMode
    success = controller_flip.set_noise_mode(NoiseMode.ANC)
    assert success is False
    assert "ANC is not supported" in controller_flip.last_error

    # Power off on TWS earbuds (must be put in case instead)
    controller_tws = HeadsetController(simulate=True, model_id="tune_230nc_tws")
    success = controller_tws.power_off()
    assert success is False
    assert "not supported" in controller_tws.last_error.lower()


# 15. Permission denied on the socket
@pytest.mark.fault
def test_fault_permission_denied_socket(isolated_env):
    """Simulate PermissionError accessing raw Bluetooth socket."""
    fake_sock = FakeRFCOMMSocket(fail_on_connect=PermissionError("Operation not permitted"))
    conn = FakeBluetoothConnection("11:22:33:44:55:66", channel=21, fake_socket=fake_sock)
    assert conn.connect() is False
    assert "Permission denied" in conn.last_error
    assert not conn.connected


# 16. Concurrent second instance
@pytest.mark.fault
def test_fault_concurrent_second_instance(isolated_env):
    """Simulate second concurrent instance attempting to run."""
    with SingleInstanceLock(lock_name="test_jblpc.lock"):
        # Second instance within same environment
        with pytest.raises(InstanceLockError) as exc_info:
            with SingleInstanceLock(lock_name="test_jblpc.lock"):
                pass
        assert "Another instance" in str(exc_info.value)


# 17. KeyboardInterrupt handling
@pytest.mark.fault
def test_fault_keyboard_interrupt(isolated_env):
    """Simulate user pressing Ctrl+C; CLI must return exit code 130 without traceback."""
    with patch("jblpc.cli.load_config", side_effect=KeyboardInterrupt):
        ret = run_cli(["status"])
        assert ret == 130


# 18. SIGTERM handling
@pytest.mark.fault
def test_fault_sigterm_handling(isolated_env):
    """Simulate process termination via SIGTERM."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(10)"],
    )
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=5)
    assert proc.returncode in (-signal.SIGTERM, 143)


# 19. Terminal too small for TUI
@pytest.mark.fault
@pytest.mark.asyncio
async def test_fault_terminal_too_small_tui(isolated_env):
    """Simulate small terminal dimensions (e.g. 35x10); TUI must not crash."""
    from jblpc.tui.app import JBLPcApp
    controller = HeadsetController(simulate=True, model_id="tune_770nc")
    app = JBLPcApp(controller)

    # Run in very constrained 35x10 size
    async with app.run_test(size=(35, 10)) as pilot:
        await pilot.pause()
        # Should remain alive and responsive to quit
        await pilot.press("q")


# 20. Non-UTF8 device name
@pytest.mark.fault
def test_fault_non_utf8_device_name(isolated_env):
    """Simulate Bluetooth device with non-UTF8 / corrupt bytes in its name."""
    mock_res = MagicMock()
    # Malformed bytes \xff\xfe in device name
    mock_res.stdout = b"Device 11:22:33:44:55:66 JBL Tune 770NC\xff\xfe Test\n"
    with patch("subprocess.run", return_value=mock_res):
        devices = find_jbl_devices()
        assert len(devices) == 1
        # Replaced with unicode replacement character \ufffd without throwing UnicodeDecodeError
        assert "\ufffd" in devices[0]["name"]
