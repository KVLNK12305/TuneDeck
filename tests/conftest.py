"""
Pytest configuration, fixtures, fake RFCOMM transports, and isolated environments.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from typing import Optional

from jblpc.protocol import (
    BluetoothConnection,
    Frame,
    FRAME_TYPE_RESPONSE,
    OP_NOISE_SET,
    OP_NOISE_GET,
    OP_BATTERY_GET,
    OP_POWER_OFF,
    build_request,
)


def pytest_addoption(parser):
    """Add CLI flags for optional real-hardware testing."""
    parser.addoption(
        "--hardware",
        action="store_true",
        default=False,
        help="Run real-hardware Bluetooth tests against a paired physical JBL device.",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "hardware: real Bluetooth hardware test")
    config.addinivalue_line("markers", "cli: CLI end-to-end test")
    config.addinivalue_line("markers", "tui: Textual TUI test")
    config.addinivalue_line("markers", "protocol: protocol parser/builder test")
    config.addinivalue_line("markers", "fault: fault injection test")
    config.addinivalue_line("markers", "health: battery health test")


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """
    Provides a completely isolated filesystem environment for tests.
    Sets isolated HOME, XDG_CONFIG_HOME, XDG_DATA_HOME, and XDG_RUNTIME_DIR.
    """
    home = tmp_path / "home"
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    runtime_dir = tmp_path / "runtime"

    home.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

    # Also clear JBL_BD by default so tests don't pick up ambient system settings
    monkeypatch.delenv("JBL_BD", raising=False)

    return {
        "home": home,
        "config_dir": config_dir,
        "data_dir": data_dir,
        "runtime_dir": runtime_dir,
    }


class FakeRFCOMMSocket:
    """Mock socket simulating RFCOMM behavior with programmable failure injection."""

    def __init__(
        self,
        fail_on_connect: Optional[Exception] = None,
        fail_on_send: Optional[Exception] = None,
        fail_on_recv: Optional[Exception] = None,
        disconnect_mid_read: bool = False,
        response_queue: Optional[list[bytes]] = None,
    ):
        self.fail_on_connect = fail_on_connect
        self.fail_on_send = fail_on_send
        self.fail_on_recv = fail_on_recv
        self.disconnect_mid_read = disconnect_mid_read
        self.response_queue = response_queue or []
        self.sent_data: list[bytes] = []
        self.closed = False
        self._connected = False
        self._timeout = 5.0

    def settimeout(self, timeout: float):
        self._timeout = timeout

    def connect(self, addr_tuple):
        if self.fail_on_connect:
            raise self.fail_on_connect
        self._connected = True

    def sendall(self, data: bytes):
        if self.closed or not self._connected:
            raise BrokenPipeError("Socket is closed or not connected.")
        if self.fail_on_send:
            raise self.fail_on_send
        self.sent_data.append(data)

    def recv(self, bufsize: int = 4096) -> bytes:
        if self.closed:
            return b""
        if self.fail_on_recv:
            raise self.fail_on_recv
        if self.disconnect_mid_read:
            self.closed = True
            return b""
        if self.response_queue:
            return self.response_queue.pop(0)
        return b""

    def close(self):
        self.closed = True
        self._connected = False


class FakeBluetoothConnection(BluetoothConnection):
    """Subclass of BluetoothConnection injected with a FakeRFCOMMSocket."""

    def __init__(
        self,
        address: str = "AA:BB:CC:DD:EE:FF",
        channel: int = 21,
        fake_socket: Optional[FakeRFCOMMSocket] = None,
    ):
        super().__init__(address=address, channel=channel)
        self.fake_socket = fake_socket or FakeRFCOMMSocket()

    def connect(self, timeout: float = 5.0) -> bool:
        if self.connected:
            return True
        if self.fake_socket.fail_on_connect:
            err = self.fake_socket.fail_on_connect
            if isinstance(err, PermissionError):
                self.last_error = f"Permission denied connecting to Bluetooth socket: {err}"
            elif isinstance(err, ConnectionRefusedError):
                self.last_error = f"Connection refused by {self.address} on RFCOMM channel {self.channel}: {err}"
            elif isinstance(err, TimeoutError):
                self.last_error = f"Connection timeout after {timeout}s connecting to {self.address}: {err}"
            else:
                self.last_error = f"Failed to connect to {self.address}: {err}"
            return False

        self._sock = self.fake_socket
        self.fake_socket._connected = True
        return True
