"""
Airoha RACE protocol implementation for JBL headphones, earbuds, and speakers.

Handles RFCOMM communication, packet framing, and command encoding/decoding.
Based on community reverse-engineering of the Airoha RACE protocol.

Protocol frame format:
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  0x05    │  Type    │  Length  │  Opcode  │ Payload  │
│  (magic) │  (1B)    │  (2B LE) │  (2B LE) │ (var)    │
└──────────┴──────────┴──────────┴──────────┴──────────┘
"""

import socket
import struct
import time
import datetime
import subprocess
import re
import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Callable

from .exceptions import (
    ConfigError,
    BluetoothAdapterError,
    DeviceNotPairedError,
    ConnectionError as JBLConnectionError,
    ProtocolError,
)

# ─── Constants ───────────────────────────────────────────────────────────────

RFCOMM_CHANNEL = 21
MAGIC_BYTE = 0x05
FRAME_TYPE_REQUEST = 0x5A
FRAME_TYPE_RESPONSE = 0x5B
FRAME_TYPE_NOTIFICATION = 0x5C

MAX_FRAME_LENGTH = 4096

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def is_valid_mac(address: str) -> bool:
    """Validate Bluetooth MAC address format (XX:XX:XX:XX:XX:XX)."""
    if not address or not isinstance(address, str):
        return False
    return bool(MAC_REGEX.match(address.strip()))


def get_config_dir() -> Path:
    """Return configuration directory for TuneDeck / JBLPc across platforms."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        base = Path(xdg)
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    tunedeck_dir = base / "tunedeck"
    jblpc_dir = base / "jblpc"
    if tunedeck_dir.exists() and (tunedeck_dir / "config.json").exists():
        return tunedeck_dir
    return jblpc_dir


def get_config_file() -> Path:
    """Return configuration file path."""
    return get_config_dir() / "config.json"


CONFIG_DIR = get_config_dir()
CONFIG_FILE = get_config_file()


class NoiseMode(IntEnum):
    """Noise control modes supported by JBL headsets."""
    OFF = 0x00
    ANC = 0x01
    TALKTHRU = 0x09
    AMBIENT_AWARE = 0x0A


class EQPreset(IntEnum):
    """EQ presets."""
    FLAT = 0x00
    JAZZ = 0x01
    VOCAL = 0x02
    BASS = 0x03
    CLUB = 0x04
    CUSTOM = 0xFF


MODE_NAMES = {
    NoiseMode.OFF: "Off",
    NoiseMode.ANC: "ANC",
    NoiseMode.TALKTHRU: "TalkThru",
    NoiseMode.AMBIENT_AWARE: "Ambient Aware",
}

EQ_PRESET_NAMES = {
    EQPreset.FLAT: "Flat",
    EQPreset.JAZZ: "Jazz",
    EQPreset.VOCAL: "Vocal",
    EQPreset.BASS: "Bass Boost",
    EQPreset.CLUB: "Club",
    EQPreset.CUSTOM: "Custom",
}

# Noise control setter payloads (verified from community RE)
NOISE_SETTERS = {
    NoiseMode.ANC: bytes.fromhex("000A01"),
    NoiseMode.OFF: bytes.fromhex("000B"),
    NoiseMode.AMBIENT_AWARE: bytes.fromhex("000A0A"),
    NoiseMode.TALKTHRU: bytes.fromhex("000A09"),
}

# Known opcodes
OP_NOISE_SET = 0x0E06          # Set noise control mode (verified Airoha RACE command for JBL)
OP_NOISE_SET_LEGACY = 0x0908   # Legacy/fallback noise set opcode
OP_NOISE_GET = 0x0901          # Get/response noise control mode
OP_NOISE_GET_PAYLOAD = bytes.fromhex("0500")  # Query payload for noise status
OP_BATTERY_PERCENTAGE = 0x0403 # Battery percentage reading
OP_BATTERY_GET = 0x0402        # Battery status / PMU register
OP_POWER_OFF = 0x0104          # Power off the device
OP_EQ_SET = 0x0A01             # Set EQ
OP_EQ_GET = 0x0A02             # Get EQ
OP_DEVICE_INFO = 0x0201        # Device info request


# ─── Checksum Calculation ────────────────────────────────────────────────────

def calculate_checksum(data: bytes) -> int:
    """Calculate 8-bit two's complement checksum for a RACE frame."""
    return (-sum(data)) & 0xFF


def verify_checksum(data_with_checksum: bytes) -> bool:
    """Verify that the checksum byte at the end of the data matches."""
    if len(data_with_checksum) < 2:
        return False
    expected = calculate_checksum(data_with_checksum[:-1])
    return data_with_checksum[-1] == expected


# ─── Frame Building & Parsing ────────────────────────────────────────────────

def build_request(opcode: int, payload: bytes = b"", with_checksum: bool = False) -> bytes:
    """Build an Airoha RACE request frame."""
    length = 2 + len(payload)
    if with_checksum:
        length += 1
    header = struct.pack("<BBH", MAGIC_BYTE, FRAME_TYPE_REQUEST, length)
    op = struct.pack("<H", opcode)
    frame = header + op + payload
    if with_checksum:
        chk = calculate_checksum(frame)
        frame += bytes([chk])
    return frame


@dataclass
class Frame:
    """A parsed protocol frame."""
    frame_type: int
    opcode: int
    payload: bytes
    timestamp: str = ""
    has_valid_checksum: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    @property
    def type_name(self) -> str:
        names = {
            FRAME_TYPE_REQUEST: "REQ",
            FRAME_TYPE_RESPONSE: "RSP",
            FRAME_TYPE_NOTIFICATION: "NTF",
        }
        return names.get(self.frame_type, f"0x{self.frame_type:02X}")

    @property
    def noise_mode(self) -> Optional[NoiseMode]:
        """Extract noise mode from a noise status response or notification."""
        if self.opcode == OP_NOISE_GET and len(self.payload) >= 4:
            try:
                return NoiseMode(self.payload[3])
            except ValueError:
                return None
        if self.opcode in (OP_NOISE_SET, OP_NOISE_SET_LEGACY) and len(self.payload) >= 2:
            if self.payload.startswith(b"\x00\x0b"):
                return NoiseMode.OFF
            elif self.payload.startswith(b"\x00\x0a\x01"):
                return NoiseMode.ANC
            elif self.payload.startswith(b"\x00\x0a\x0a"):
                return NoiseMode.AMBIENT_AWARE
            elif self.payload.startswith(b"\x00\x0a\x09"):
                return NoiseMode.TALKTHRU
        return None

    @property
    def battery_level(self) -> Optional[int]:
        """Extract battery percentage from a battery response."""
        if self.opcode == OP_BATTERY_PERCENTAGE and len(self.payload) >= 1:
            val = self.payload[-1]
            if 0 <= val <= 100:
                return val
        if self.opcode == OP_BATTERY_GET and len(self.payload) >= 1:
            val = self.payload[0]
            if 0 <= val <= 100:
                return val
        return None

    def __repr__(self):
        return (
            f"Frame({self.type_name}, op=0x{self.opcode:04X}, "
            f"body={self.payload.hex(' ')}, t={self.timestamp})"
        )


def parse_frames(
    buf: bytes,
    verify_checksum_byte: bool = False,
) -> tuple[list[Frame], bytes]:
    """
    Parse complete frames from a byte buffer.
    Discards garbage bytes before the magic byte and oversized frames.
    Returns (list_of_frames, remaining_bytes).
    """
    frames = []
    while len(buf) >= 4:
        # 1. Skip garbage bytes until MAGIC_BYTE
        if buf[0] != MAGIC_BYTE:
            next_magic = buf.find(bytes([MAGIC_BYTE]), 1)
            if next_magic == -1:
                # No magic byte in the buffer, discard all
                buf = b""
                break
            buf = buf[next_magic:]
            if len(buf) < 4:
                break

        frame_type = buf[1]
        length = struct.unpack_from("<H", buf, 2)[0]

        # 2. Check for oversized / corrupted frame length
        if length > MAX_FRAME_LENGTH:
            # Corrupted frame length: drop magic byte and seek next
            buf = buf[1:]
            continue

        total = 4 + length  # header(4) + payload length
        if len(buf) < total:
            # Incomplete frame, wait for more chunks
            break

        opcode = struct.unpack_from("<H", buf, 4)[0]

        if verify_checksum_byte:
            # Checksum is the last byte
            frame_data = buf[:total - 1]
            actual_checksum = buf[total - 1]
            expected_checksum = calculate_checksum(frame_data)
            if actual_checksum != expected_checksum:
                raise ProtocolError(
                    f"Frame checksum mismatch: expected 0x{expected_checksum:02X}, "
                    f"got 0x{actual_checksum:02X}"
                )
            payload = buf[6:total - 1]
        else:
            payload = buf[6:total]

        frames.append(Frame(frame_type, opcode, payload))
        buf = buf[total:]

    return frames, buf


# ─── Configuration ───────────────────────────────────────────────────────────

def load_config() -> dict:
    """
    Load configuration from file or environment.
    Raises ConfigError if config.json is corrupt, empty, or unreadable.
    """
    config = {
        "bluetooth_address": "",
        "rfcomm_channel": 21,
        "auto_connect": True,
        "eq_bands": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    }

    env_addr = (os.environ.get("TUNEDECK_BD") or os.environ.get("JBL_BD") or "").strip()
    if env_addr:
        config["bluetooth_address"] = env_addr

    config_file = get_config_file()
    if not config_file.exists():
        alt = get_config_dir().parent / "tunedeck" / "config.json"
        if alt.exists():
            config_file = alt

    if config_file.exists():
        try:
            content = config_file.read_text(encoding="utf-8")
            if not content.strip():
                raise ConfigError(f"Configuration file {config_file} is empty.")
            file_config = json.loads(content)
            if not isinstance(file_config, dict):
                raise ConfigError(f"Configuration in {config_file} must be a JSON object.")
            config.update(file_config)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Corrupt configuration file {config_file}: {e}") from e
        except OSError as e:
            raise ConfigError(f"Cannot read configuration file {config_file}: {e}") from e

    # Environment variable takes precedence
    if env_addr:
        config["bluetooth_address"] = env_addr

    return config


def save_config(config: dict):
    """Save configuration to file."""
    config_dir = get_config_dir()
    config_file = get_config_file()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        raise ConfigError(f"Cannot write configuration file {config_file}: {e}") from e


# ─── Bluetooth Connection ────────────────────────────────────────────────────

class BluetoothConnection:
    """Manages the Bluetooth RFCOMM socket connection to the device."""

    def __init__(self, address: str, channel: int = RFCOMM_CHANNEL):
        self.address = address
        self.channel = channel
        self._sock: Optional[socket.socket] = None
        self._buffer = b""
        self.last_error: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self, timeout: float = 5.0) -> bool:
        """Establish RFCOMM connection to the device."""
        if self.connected:
            return True

        self.last_error = None
        if not self.address:
            self.last_error = "No Bluetooth address specified."
            return False

        if not is_valid_mac(self.address):
            self.last_error = f"Invalid Bluetooth MAC address: '{self.address}'."
            return False

        if not hasattr(socket, "AF_BLUETOOTH"):
            if sys.platform == "darwin":
                self.last_error = (
                    "Bluetooth sockets (AF_BLUETOOTH) are not supported natively by Python on macOS. "
                    "Use simulation mode (tunedeck --sim / tunedeck-gui --sim) or an RFCOMM serial bridge."
                )
            else:
                self.last_error = "Bluetooth sockets (AF_BLUETOOTH) are not supported on this platform."
            return False

        try:
            sock = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )
            sock.settimeout(timeout)
            sock.connect((self.address, self.channel))
            self._sock = sock
            self._buffer = b""
            return True
        except PermissionError as e:
            self._sock = None
            self.last_error = f"Permission denied accessing Bluetooth socket: {e}"
            return False
        except ConnectionRefusedError as e:
            self._sock = None
            self.last_error = f"Connection refused by {self.address} on RFCOMM channel {self.channel}: {e}"
            return False
        except (socket.timeout, TimeoutError) as e:
            self._sock = None
            self.last_error = f"Connection timeout after {timeout}s connecting to {self.address}: {e}"
            return False
        except (OSError, socket.error) as e:
            self._sock = None
            self.last_error = f"Failed to connect to {self.address}: {e}"
            return False

    def disconnect(self):
        """Close the RFCOMM connection."""
        if self._sock:
            try:
                self._sock.close()
            except OSError as e:
                self.last_error = f"Error closing socket: {e}"
            self._sock = None
            self._buffer = b""

    def send(self, data: bytes) -> bool:
        """Send raw bytes over the RFCOMM socket."""
        if not self.connected:
            self.last_error = "Cannot send: not connected."
            return False
        try:
            self._sock.sendall(data)
            return True
        except (OSError, socket.error) as e:
            self.last_error = f"Send error: {e}"
            self.disconnect()
            return False

    def send_command(self, opcode: int, payload: bytes = b"", with_checksum: bool = False) -> bool:
        """Build and send a protocol command."""
        frame = build_request(opcode, payload, with_checksum=with_checksum)
        return self.send(frame)

    def receive(self, timeout: float = 2.0, verify_checksum_byte: bool = False) -> list[Frame]:
        """Receive and parse protocol frames non-blocking with timeout."""
        if not self.connected:
            return []

        frames = []
        end_time = time.monotonic() + timeout

        while True:
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                break

            self._sock.settimeout(min(0.2, remaining))
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    self.last_error = "Remote device disconnected unexpectedly mid-session."
                    self.disconnect()
                    break
                self._buffer += chunk
            except socket.timeout:
                if not self._buffer:
                    continue
            except (OSError, socket.error) as e:
                self.last_error = f"Receive error: {e}"
                self.disconnect()
                break

            parsed, self._buffer = parse_frames(self._buffer, verify_checksum_byte=verify_checksum_byte)
            frames.extend(parsed)

            if frames:
                break

        return frames

    def send_and_receive(
        self,
        opcode: int,
        payload: bytes = b"",
        timeout: float = 2.0,
        expect_opcode: Optional[int] = None,
        verify_checksum_byte: bool = False,
    ) -> list[Frame]:
        """Send a command and wait for response frames."""
        if not self.send_command(opcode, payload):
            return []
        frames = self.receive(timeout, verify_checksum_byte=verify_checksum_byte)
        if expect_opcode is not None and frames:
            if frames[0].opcode != expect_opcode:
                raise ProtocolError(
                    f"Unexpected response opcode: expected 0x{expect_opcode:04X}, "
                    f"got 0x{frames[0].opcode:04X}"
                )
        return frames


def find_windows_jbl_devices() -> list[dict]:
    """Discover paired JBL devices on Windows via PowerShell."""
    devices = []
    try:
        cmd = [
            "powershell.exe", "-NoProfile", "-Command",
            "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
            "Where-Object { $_.FriendlyName -match 'JBL|770|Live|Tour|Flip|Charge|Pulse|PartyBox' } | "
            "Select-Object FriendlyName, InstanceId | ConvertTo-Json"
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
        if res.returncode == 0 and res.stdout.strip():
            raw = json.loads(res.stdout)
            items = raw if isinstance(raw, list) else [raw]
            for item in items:
                name = item.get("FriendlyName", "").strip()
                inst_id = item.get("InstanceId", "")
                match = re.search(r"DEV_([0-9A-Fa-f]{12})", inst_id)
                if match:
                    raw_mac = match.group(1).upper()
                    formatted_mac = ":".join(raw_mac[i:i+2] for i in range(0, 12, 2))
                    devices.append({"address": formatted_mac, "name": name})
                elif name:
                    devices.append({"address": "", "name": name})
    except Exception as err:
        devices = []
    return devices


def find_macos_jbl_devices() -> list[dict]:
    """Discover paired JBL devices on macOS via system_profiler."""
    devices = []
    try:
        res = subprocess.run(
            ["system_profiler", "SPBluetoothDataType", "-json"],
            capture_output=True,
            timeout=5
        )
        if res.returncode == 0:
            data = json.loads(res.stdout.decode("utf-8", errors="replace"))
            bt_items = data.get("SPBluetoothDataType", [{}])
            if bt_items:
                bt_data = bt_items[0]
                raw_devices = []
                if "devices_list" in bt_data:
                    raw_devices = bt_data["devices_list"]
                else:
                    for k in ("device_connected", "device_not_connected"):
                        sub = bt_data.get(k, [])
                        if isinstance(sub, list):
                            raw_devices.extend(sub)
                        elif isinstance(sub, dict):
                            for dev_name, info in sub.items():
                                raw_devices.append({dev_name: info})

                for item in raw_devices:
                    if isinstance(item, dict):
                        for dev_name, dev_info in item.items():
                            upper = dev_name.upper()
                            if any(kw in upper for kw in ("JBL", "770", "LIVE", "TOUR", "FLIP", "CHARGE", "PULSE", "PARTYBOX")):
                                addr = ""
                                if isinstance(dev_info, dict):
                                    addr = dev_info.get("device_address", "") or dev_info.get("device_mac", "")
                                addr = addr.replace("-", ":").upper()
                                devices.append({"address": addr, "name": dev_name})
    except Exception as err:
        devices = []
    return devices


# ─── Device Discovery & System Probing ──────────────────────────────────────

def check_bluetoothctl_available():
    """Verify that bluetoothctl is installed and accessible (Linux)."""
    try:
        subprocess.run(["bluetoothctl", "--version"], capture_output=True, timeout=3)
    except FileNotFoundError:
        raise BluetoothAdapterError("bluetoothctl utility is not installed on this system.")
    except subprocess.TimeoutExpired:
        raise BluetoothAdapterError("bluetoothctl timed out checking version.")


def check_bluetooth_adapter_powered():
    """Verify that the local Bluetooth controller exists and is powered on."""
    if sys.platform == "win32":
        try:
            cmd = ["powershell.exe", "-NoProfile", "-Command",
                   "(Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue).Count"]
            res = subprocess.run(cmd, capture_output=True, timeout=4, text=True)
            if res.returncode == 0:
                count = int(res.stdout.strip() or "0")
                if count == 0:
                    raise BluetoothAdapterError("Bluetooth adapter is powered off or missing.")
                return
        except BluetoothAdapterError:
            raise
        except Exception as err:
            err_msg = str(err)

        if hasattr(socket, "AF_BLUETOOTH"):
            try:
                s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                s.close()
                return
            except Exception as e:
                raise BluetoothAdapterError("Bluetooth adapter is powered off or missing.") from e
        return
    elif sys.platform == "darwin":
        try:
            res = subprocess.run(["system_profiler", "SPBluetoothDataType", "-json"],
                                 capture_output=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout.decode("utf-8", errors="replace"))
                bt_items = data.get("SPBluetoothDataType", [{}])
                if bt_items:
                    props = bt_items[0].get("controller_properties", {})
                    state = props.get("controller_state", "")
                    if state and "off" in state.lower():
                        raise BluetoothAdapterError("Bluetooth adapter is powered off or missing.")
                    return
        except BluetoothAdapterError:
            raise
        except Exception as err:
            err_msg = str(err)
        return

    # Linux (BlueZ / bluetoothctl)
    check_bluetoothctl_available()
    try:
        res = subprocess.run(["bluetoothctl", "show"], capture_output=True, timeout=5)
        stdout = res.stdout.decode("utf-8", errors="replace")
        if "No default controller available" in stdout or "Powered: no" in stdout:
            raise BluetoothAdapterError("Bluetooth adapter is powered off or missing.")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise BluetoothAdapterError(f"Bluetooth adapter check failed: {e}") from e


def find_jbl_devices() -> list[dict]:
    """Discover paired JBL devices across platforms."""
    if sys.platform == "win32":
        return find_windows_jbl_devices()
    elif sys.platform == "darwin":
        return find_macos_jbl_devices()

    # Linux (BlueZ / bluetoothctl)
    check_bluetoothctl_available()
    devices = []
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            timeout=5
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        for line in stdout.splitlines():
            match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)", line)
            if match:
                addr, name = match.groups()
                if "JBL" in name.upper() or "770" in name:
                    devices.append({"address": addr, "name": name.strip()})
    except subprocess.TimeoutExpired:
        raise BluetoothAdapterError("bluetoothctl timed out while listing devices.")
    return devices


def check_device_connected(address: str) -> bool:
    """Check if a Bluetooth device is currently connected."""
    if not address:
        return False
    if sys.platform == "win32":
        try:
            clean_addr = address.replace(":", "").replace("-", "")
            cmd = ["powershell.exe", "-NoProfile", "-Command",
                   f"Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
                   f"Where-Object {{ $_.InstanceId -like '*{clean_addr}*' }} | "
                   f"Select-Object -ExpandProperty Status"]
            res = subprocess.run(cmd, capture_output=True, timeout=4, text=True)
            if res.returncode == 0:
                return "OK" in res.stdout
        except Exception as err:
            return True
        return True
    elif sys.platform == "darwin":
        try:
            devs = find_macos_jbl_devices()
            norm = address.upper().replace("-", ":")
            return any(d.get("address", "").upper() == norm for d in devs)
        except Exception as err:
            return True

    # Linux (BlueZ / bluetoothctl)
    check_bluetoothctl_available()
    try:
        result = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            timeout=5
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        if "Device " not in stdout or "not available" in stdout.lower():
            return False
        return "Connected: yes" in stdout
    except subprocess.TimeoutExpired:
        return False


def check_device_paired(address: str) -> bool:
    """Check if a Bluetooth device is paired."""
    if not address:
        return False
    if sys.platform == "win32":
        try:
            devs = find_windows_jbl_devices()
            norm = address.upper().replace("-", ":")
            if any(d.get("address", "").upper() == norm for d in devs if d.get("address")):
                return True
            clean_addr = address.replace(":", "").replace("-", "")
            cmd = ["powershell.exe", "-NoProfile", "-Command",
                   f"(Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
                   f"Where-Object {{ $_.InstanceId -like '*{clean_addr}*' }}).Count"]
            res = subprocess.run(cmd, capture_output=True, timeout=4, text=True)
            if res.returncode == 0:
                return int(res.stdout.strip() or "0") > 0
        except Exception as err:
            return True
        return True
    elif sys.platform == "darwin":
        try:
            devs = find_macos_jbl_devices()
            norm = address.upper().replace("-", ":")
            if any(d.get("address", "").upper() == norm for d in devs if d.get("address")):
                return True
            return len(devs) > 0
        except Exception as err:
            return True

    # Linux (BlueZ / bluetoothctl)
    check_bluetoothctl_available()
    try:
        result = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            timeout=5
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        return "Paired: yes" in stdout
    except subprocess.TimeoutExpired:
        return False


def get_system_battery_level(address: str) -> Optional[int]:
    """
    Get battery percentage reported by the operating system Bluetooth subsystem
    (Linux BlueZ/bluetoothctl/UPower, macOS system_profiler, Windows PowerShell/PnP).
    Returns integer 0-100 or None if unavailable.
    """
    if not address:
        return None

    if sys.platform == "win32":
        try:
            clean_addr = address.replace(":", "").replace("-", "")
            cmd = [
                "powershell.exe", "-NoProfile", "-Command",
                f"$dev = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {{ $_.InstanceId -like '*{clean_addr}*' }} | Select-Object -First 1; "
                "if ($dev) { (Get-PnpDeviceProperty -InstanceId $dev.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue).Data }"
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=4, text=True)
            if res.returncode == 0:
                raw = res.stdout.strip()
                if raw.isdigit():
                    val = int(raw)
                    if 0 <= val <= 100:
                        return val
        except Exception:
            pass
        return None

    elif sys.platform == "darwin":
        try:
            res = subprocess.run(["system_profiler", "SPBluetoothDataType", "-json"],
                                 capture_output=True, timeout=5)
            if res.returncode == 0:
                raw_json = res.stdout.decode("utf-8", errors="replace")
                m = re.search(r'"(?:device_batteryLevelMain|batteryPercentCase|battery_percent)"\s*:\s*"?(\d+)"?', raw_json)
                if m:
                    val = int(m.group(1))
                    if 0 <= val <= 100:
                        return val
        except Exception:
            pass
        return None

    # Linux (BlueZ / bluetoothctl / UPower)
    try:
        check_bluetoothctl_available()
        res = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            timeout=5
        )
        stdout = res.stdout.decode("utf-8", errors="replace")
        m = re.search(r"Battery Percentage:\s*(?:0x[0-9a-fA-F]+\s*\()?(\d+)\)?", stdout)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val
    except Exception:
        pass

    # Optional fallback to upower on Linux
    try:
        res = subprocess.run(["upower", "-e"], capture_output=True, timeout=3, text=True)
        if res.returncode == 0:
            mac_clean = address.replace(":", "_").lower()
            for line in res.stdout.splitlines():
                if mac_clean in line.lower() or "headset" in line.lower():
                    info = subprocess.run(["upower", "-i", line.strip()], capture_output=True, timeout=3, text=True)
                    m = re.search(r"percentage:\s*(\d+)%", info.stdout)
                    if m:
                        val = int(m.group(1))
                        if 0 <= val <= 100:
                            return val
    except Exception:
        pass

    return None

