"""
Subprocess-based BlueZ backend for JBL device discovery and battery monitoring.

This module re-implements the Linux-specific bluetoothctl / upower calls from
``jblpc.protocol`` as a standalone backend with a clean interface.  It serves
as the fallback when native D-Bus (``linux_dbus``) is unavailable.
"""

import re
import shutil
import subprocess
import sys
from typing import Optional

from ..exceptions import BluetoothAdapterError


# ─── Constants ───────────────────────────────────────────────────────────────

# Harman's Bluetooth SIG company IDs: 0x0057 (Harman International Industries)
# and 0x075A (HARMAN CO.,LTD.).
HARMAN_VENDOR_REGEX = re.compile(
    r"Modalias:\s*bluetooth:v(0057|075A)", re.IGNORECASE
)
AIROHA_RACE_UUID = "5052494d-2dab-0341-6972-6f6861424c45"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_jbl_device_name(name: str) -> bool:
    """Check if a Bluetooth broadcast name belongs to a JBL device."""
    if not name or not isinstance(name, str):
        return False
    return "JBL" in name.upper()


def _is_harman_jbl_info(info_stdout: str) -> tuple[bool, str]:
    """
    Examines bluetoothctl info output.
    Returns (is_jbl, hardware_name).
    Identifies JBL devices via Harman Bluetooth SIG vendor ID (0x0057 / 0x075A),
    Airoha RACE protocol UUID, or factory hardware broadcast Name.
    """
    if not info_stdout:
        return False, ""

    m_name = re.search(r"^\s*Name:\s*(.+)$", info_stdout, re.MULTILINE)
    hw_name = m_name.group(1).strip() if m_name else ""
    m_alias = re.search(r"^\s*Alias:\s*(.+)$", info_stdout, re.MULTILINE)
    alias = m_alias.group(1).strip() if m_alias else ""

    if HARMAN_VENDOR_REGEX.search(info_stdout):
        return True, hw_name or alias
    if AIROHA_RACE_UUID in info_stdout.lower():
        return True, hw_name or alias
    if _is_jbl_device_name(hw_name) or _is_jbl_device_name(alias):
        return True, hw_name or alias

    return False, hw_name or alias


def _check_bluetoothctl_available():
    """Verify that bluetoothctl is installed and accessible."""
    try:
        subprocess.run(["bluetoothctl", "--version"], capture_output=True, timeout=3)
    except FileNotFoundError:
        raise BluetoothAdapterError(
            "bluetoothctl utility is not installed on this system."
        )
    except subprocess.TimeoutExpired:
        raise BluetoothAdapterError("bluetoothctl timed out checking version.")
    _check_bluetooth_service_running()


def _check_bluetooth_service_running():
    """Fail fast when the BlueZ daemon is stopped.

    Only checked where systemd is available (not inside Flatpak sandboxes).
    """
    if not shutil.which("systemctl"):
        return
    try:
        res = subprocess.run(
            ["systemctl", "is-active", "bluetooth"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return
    state = res.stdout.strip() if isinstance(res.stdout, str) else ""
    if state in ("inactive", "failed"):
        raise BluetoothAdapterError(
            "The Bluetooth service is not running. "
            "Start it with: sudo systemctl enable --now bluetooth"
        )


# ─── Public API ──────────────────────────────────────────────────────────────

def find_jbl_devices_subprocess() -> list[dict]:
    """Discover paired and connected JBL devices on Linux via bluetoothctl.

    Returns list of dicts:
    ``[{"address": "AA:BB:...", "name": "JBL Tune 770NC", "connected": True}, ...]``
    """
    _check_bluetoothctl_available()

    devices = []
    seen: set[str] = set()

    try:
        # 1. Query currently connected devices first
        connected_macs: set[str] = set()
        try:
            conn_res = subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                capture_output=True,
                timeout=3,
            )
            conn_stdout = conn_res.stdout.decode("utf-8", errors="replace")
            for cline in conn_stdout.splitlines():
                cm = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s*(.*)", cline)
                if cm:
                    c_addr = cm.group(1).upper()
                    c_name = cm.group(2).strip()
                    connected_macs.add(c_addr)
                    if _is_jbl_device_name(c_name):
                        seen.add(c_addr)
                        devices.append(
                            {"address": cm.group(1), "name": c_name, "connected": True}
                        )
                    else:
                        try:
                            info_res = subprocess.run(
                                ["bluetoothctl", "info", cm.group(1)],
                                capture_output=True,
                                timeout=2,
                            )
                            is_jbl, true_name = _is_harman_jbl_info(
                                info_res.stdout.decode("utf-8", errors="replace")
                            )
                            if is_jbl:
                                seen.add(c_addr)
                                devices.append(
                                    {
                                        "address": cm.group(1),
                                        "name": true_name or c_name,
                                        "connected": True,
                                    }
                                )
                        except Exception:
                            pass
        except Exception:
            pass

        # 2. Query all known/paired Bluetooth devices
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            timeout=5,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")

        for line in stdout.splitlines():
            match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)", line)
            if match:
                addr, name = match.groups()
                addr_upper = addr.upper()
                if addr_upper in seen:
                    continue
                name_clean = name.strip()
                is_conn = addr_upper in connected_macs
                if _is_jbl_device_name(name_clean):
                    seen.add(addr_upper)
                    devices.append(
                        {"address": addr, "name": name_clean, "connected": is_conn}
                    )
                elif is_conn:
                    try:
                        info_res = subprocess.run(
                            ["bluetoothctl", "info", addr],
                            capture_output=True,
                            timeout=2,
                        )
                        is_jbl, true_name = _is_harman_jbl_info(
                            info_res.stdout.decode("utf-8", errors="replace")
                        )
                        if is_jbl:
                            seen.add(addr_upper)
                            devices.append(
                                {
                                    "address": addr,
                                    "name": true_name or name_clean,
                                    "connected": True,
                                }
                            )
                    except Exception:
                        pass
    except subprocess.TimeoutExpired:
        raise BluetoothAdapterError(
            "bluetoothctl timed out while listing devices."
        )

    # Sort: connected devices first, then alphabetically by name
    devices.sort(key=lambda d: (0 if d.get("connected") else 1, d.get("name", "")))
    return devices


def get_system_battery_level_subprocess(address: str) -> Optional[int]:
    """Get battery percentage via bluetoothctl / upower.

    Returns integer 0-100 or None if unavailable.
    """
    if not address:
        return None

    # 1. Try bluetoothctl info
    try:
        _check_bluetoothctl_available()
        res = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            timeout=5,
        )
        stdout = res.stdout.decode("utf-8", errors="replace")
        m = re.search(
            r"Battery Percentage:\s*(?:0x[0-9a-fA-F]+\s*\()?(\\d+)\)?", stdout
        )
        if not m:
            m = re.search(
                r"Battery Percentage:\s*(?:0x[0-9a-fA-F]+\s*\()?(\d+)\)?", stdout
            )
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val
    except Exception:
        pass

    # 2. Fallback to upower
    try:
        res = subprocess.run(
            ["upower", "-e"], capture_output=True, timeout=3, text=True
        )
        if res.returncode == 0:
            mac_clean = address.replace(":", "_").lower()
            for line in res.stdout.splitlines():
                if mac_clean in line.lower() or "headset" in line.lower():
                    info = subprocess.run(
                        ["upower", "-i", line.strip()],
                        capture_output=True,
                        timeout=3,
                        text=True,
                    )
                    m = re.search(r"percentage:\s*(\d+)%", info.stdout)
                    if m:
                        val = int(m.group(1))
                        if 0 <= val <= 100:
                            return val
    except Exception:
        pass

    return None


def check_device_connected_subprocess(address: str) -> bool:
    """Check if a Bluetooth device is currently connected via bluetoothctl."""
    if not address:
        return False
    _check_bluetoothctl_available()
    try:
        result = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            timeout=5,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        if "Device " not in stdout or "not available" in stdout.lower():
            return False
        return "Connected: yes" in stdout
    except subprocess.TimeoutExpired:
        return False


def check_device_paired_subprocess(address: str) -> bool:
    """Check if a Bluetooth device is paired via bluetoothctl."""
    if not address:
        return False
    _check_bluetoothctl_available()
    try:
        result = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            timeout=5,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        return "Paired: yes" in stdout
    except subprocess.TimeoutExpired:
        return False


def check_bluetooth_adapter_powered_subprocess():
    """Verify that the local Bluetooth controller exists and is powered on."""
    _check_bluetoothctl_available()
    try:
        res = subprocess.run(
            ["bluetoothctl", "show"], capture_output=True, timeout=5
        )
        stdout = res.stdout.decode("utf-8", errors="replace")
        if "No default controller available" in stdout or "Powered: no" in stdout:
            raise BluetoothAdapterError(
                "Bluetooth adapter is powered off or missing."
            )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise BluetoothAdapterError(
            f"Bluetooth adapter check failed: {e}"
        ) from e
