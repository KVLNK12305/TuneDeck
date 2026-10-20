"""
High-level headset and speaker controller.

Provides a clean API over the raw Bluetooth protocol, with simulation mode
for development/testing without the actual headset.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum

from .protocol import (
    BluetoothConnection,
    NoiseMode,
    EQPreset,
    MODE_NAMES,
    EQ_PRESET_NAMES,
    NOISE_SETTERS,
    OP_NOISE_SET,
    OP_NOISE_GET,
    OP_BATTERY_GET,
    OP_POWER_OFF,
    OP_EQ_SET,
    OP_DEVICE_INFO,
    load_config,
    save_config,
    find_jbl_devices,
    check_device_connected,
    check_device_paired,
    check_bluetooth_adapter_powered,
    is_valid_mac,
)
from .models import (
    DeviceProfile,
    DeviceCategory,
    BatteryScheme,
    EQType,
    ProtocolFamily,
    match_device_profile,
    get_profile_by_id,
    SUPPORTED_MODELS,
    GENERIC_HEADPHONES,
)
from .exceptions import (
    ConfigError,
    BluetoothAdapterError,
    DeviceNotPairedError,
    ConnectionError as JBLConnectionError,
    UnsupportedCommandError,
)
from .health import BatteryHealthTracker, generate_synthetic_history


@dataclass
class HeadsetState:
    """Current state of the headset or speaker."""
    connected: bool = False
    battery_level: int = -1
    battery_left: int = -1
    battery_right: int = -1
    battery_case: int = -1
    noise_mode: NoiseMode = NoiseMode.OFF
    eq_preset: EQPreset = EQPreset.FLAT
    eq_bands: list[int] = field(default_factory=lambda: [0] * 10)
    device_name: str = "JBL Tune 770NC"
    firmware_version: str = "Unknown"
    bt_address: str = ""
    signal_strength: int = 0
    profile: DeviceProfile = field(default_factory=lambda: SUPPORTED_MODELS[0])
    partyboost_active: bool = False

    @property
    def battery_icon(self) -> str:
        if self.battery_level < 0:
            return "🔋"
        elif self.battery_level <= 10:
            return "🪫"
        elif self.battery_level <= 25:
            return "🔋"
        elif self.battery_level <= 75:
            return "🔋"
        else:
            return "🔋"

    @property
    def noise_mode_name(self) -> str:
        return MODE_NAMES.get(self.noise_mode, "Unknown")

    @property
    def eq_preset_name(self) -> str:
        return EQ_PRESET_NAMES.get(self.eq_preset, "Unknown")

    @property
    def battery_bar(self) -> str:
        """Generate a visual battery bar."""
        if self.battery_level < 0:
            return "─── ??? ───"
        filled = int(self.battery_level / 10)
        empty = 10 - filled
        return f"{'█' * filled}{'░' * empty} {self.battery_level}%"


class HeadsetController:
    """
    Controls JBL headphones, earbuds, or speakers.
    Supports real Bluetooth and multi-device simulation modes.
    """

    def __init__(
        self,
        bt_address: str = "",
        simulate: bool = False,
        model: Optional[str] = None,
        model_id: Optional[str] = None,
        connection: Optional[BluetoothConnection] = None,
    ):
        model_name = model or model_id
        profile = None
        if model_name:
            profile = get_profile_by_id(model_name) or match_device_profile(model_name)
        else:
            profile = SUPPORTED_MODELS[0]

        initial_log = []
        initial_bands = [0] * len(profile.eq_band_frequencies)
        try:
            cfg = load_config()
            saved_bands = cfg.get("eq_bands")
            if saved_bands and len(saved_bands) == len(profile.eq_band_frequencies):
                initial_bands = [max(-12, min(12, int(b))) for b in saved_bands]
        except (ConfigError, ValueError, KeyError) as e:
            initial_log.append(f"Using default EQ bands: {e}")

        self.state = HeadsetState(
            bt_address=bt_address,
            device_name=profile.display_name,
            profile=profile,
            eq_bands=initial_bands,
        )
        self._simulate = simulate
        self._connection: Optional[BluetoothConnection] = connection
        self._listeners: list[Callable[[HeadsetState], None]] = []
        self._log: list[str] = initial_log
        self.last_error: Optional[str] = None

        if not simulate and bt_address and self._connection is None:
            self._connection = BluetoothConnection(bt_address, channel=profile.rfcomm_channel)

    @property
    def simulating(self) -> bool:
        return self._simulate

    def set_profile(self, profile: DeviceProfile):
        """Update active profile and reconfigure state."""
        self.state.profile = profile
        self.state.device_name = profile.display_name
        self.state.eq_bands = [0] * len(profile.eq_band_frequencies)
        self._notify()

    def add_listener(self, callback: Callable[[HeadsetState], None]):
        """Register a callback for state changes."""
        self._listeners.append(callback)

    def _notify(self):
        """Notify all listeners of state change."""
        for cb in self._listeners:
            try:
                cb(self.state)
            except Exception as e:
                # Do not silently pass without logging
                self._add_log(f"⚠ Listener error: {e}")

    def _add_log(self, message: str):
        """Add an entry to the activity log."""
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self._log.append(entry)
        if len(self._log) > 100:
            self._log = self._log[-100:]

    def get_log(self) -> list[str]:
        """Get the activity log."""
        return list(self._log)

    # ─── Connection ──────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect to the device."""
        self.last_error = None

        if self._simulate:
            p = self.state.profile
            self.state.connected = True
            if p.battery_scheme == BatteryScheme.TWS_TRIO:
                self.state.battery_left = random.randint(75, 95)
                self.state.battery_right = random.randint(75, 95)
                self.state.battery_case = random.randint(50, 90)
                self.state.battery_level = min(self.state.battery_left, self.state.battery_right)
            else:
                self.state.battery_level = random.randint(50, 95)

            if p.has_anc:
                self.state.noise_mode = NoiseMode.ANC
            else:
                self.state.noise_mode = NoiseMode.OFF

            self.state.eq_preset = EQPreset.FLAT
            self.state.eq_bands = [0] * len(p.eq_band_frequencies)
            self.state.firmware_version = "2.4.6 (sim)"
            self.state.signal_strength = random.randint(75, 100)
            self._add_log(f"✓ Connected to {p.display_name} (simulation)")
            self._notify()
            return True

        if not self.state.bt_address:
            self.last_error = "No Bluetooth address configured. Set JBL_BD or run 'jblpc cli scan'."
            self._add_log(f"✗ {self.last_error}")
            return False

        if not is_valid_mac(self.state.bt_address):
            self.last_error = f"Invalid Bluetooth MAC address: '{self.state.bt_address}'."
            self._add_log(f"✗ {self.last_error}")
            return False

        # System check: Adapter powered
        try:
            check_bluetooth_adapter_powered()
        except BluetoothAdapterError as e:
            self.last_error = str(e)
            self._add_log(f"✗ {self.last_error}")
            return False

        # System check: Device paired
        if not check_device_paired(self.state.bt_address):
            self.last_error = f"Device {self.state.bt_address} is not paired via Bluetooth."
            self._add_log(f"✗ {self.last_error}")
            return False

        # System check: Connected at OS level
        if not check_device_connected(self.state.bt_address):
            self.last_error = f"Device {self.state.bt_address} is paired but not currently connected at the OS level."
            self._add_log(f"✗ {self.last_error}")
            return False

        if not self._connection:
            self._connection = BluetoothConnection(
                self.state.bt_address,
                channel=self.state.profile.rfcomm_channel
            )

        success = self._connection.connect()
        if success:
            self.state.connected = True
            self._add_log("✓ RFCOMM connection established")
            self._query_battery()
            self._query_noise_mode()
        else:
            self.last_error = self._connection.last_error or f"Failed to connect to {self.state.bt_address} via RFCOMM."
            self._add_log(f"✗ {self.last_error}")

        self._notify()
        return success

    def disconnect(self):
        """Disconnect from the headset."""
        if self._simulate:
            self.state.connected = False
            self._add_log("✓ Disconnected (simulation)")
            self._notify()
            return

        if self._connection:
            self._connection.disconnect()
        self.state.connected = False
        self._add_log("✓ Disconnected")
        self._notify()

    # ─── Noise Control ───────────────────────────────────────────────────

    def set_noise_mode(self, mode: NoiseMode) -> bool:
        """Set the noise control mode (ANC, Ambient, TalkThru, Off)."""
        self.last_error = None
        p = self.state.profile

        # Capability validation
        if mode == NoiseMode.ANC and not p.has_anc:
            self.last_error = f"ANC is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

        if mode == NoiseMode.AMBIENT_AWARE and not p.has_ambient_aware:
            self.last_error = f"Ambient Aware is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

        if mode == NoiseMode.TALKTHRU and not p.has_talkthru:
            self.last_error = f"TalkThru is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

        if mode == NoiseMode.OFF and not (p.has_anc or p.has_ambient_aware or p.has_talkthru):
            self.last_error = f"Noise control is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

        if self._simulate:
            self.state.noise_mode = mode
            self._add_log(f"🔇 Noise mode → {MODE_NAMES[mode]}")
            self._notify()
            return True

        if not self.state.connected or not self._connection:
            self.last_error = "Device is not connected."
            self._add_log(f"✗ {self.last_error}")
            return False

        payload = NOISE_SETTERS.get(mode)
        if payload is None:
            self.last_error = f"Unknown noise mode: {mode}"
            self._add_log(f"✗ {self.last_error}")
            return False

        success = self._connection.send_command(OP_NOISE_SET, payload)
        if success:
            self.state.noise_mode = mode
            self._add_log(f"🔇 Noise mode → {MODE_NAMES[mode]}")

            frames = self._connection.receive(timeout=1.0)
            for frame in frames:
                if frame.noise_mode is not None:
                    self.state.noise_mode = frame.noise_mode
                    self._add_log(f"  ← Confirmed: {MODE_NAMES[frame.noise_mode]}")
        else:
            self.last_error = self._connection.last_error or "Failed to send noise command."
            self._add_log(f"✗ {self.last_error}")

        self._notify()
        return success

    def cycle_noise_mode(self) -> Optional[NoiseMode]:
        """Cycle through supported noise modes."""
        p = self.state.profile
        cycle = []
        if p.has_anc:
            cycle.append(NoiseMode.ANC)
        if p.has_ambient_aware:
            cycle.append(NoiseMode.AMBIENT_AWARE)
        if p.has_talkthru:
            cycle.append(NoiseMode.TALKTHRU)

        if not cycle:
            self.last_error = f"Noise control is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            return None

        cycle.insert(0, NoiseMode.OFF)

        current_idx = cycle.index(self.state.noise_mode) if self.state.noise_mode in cycle else -1
        next_idx = (current_idx + 1) % len(cycle)
        next_mode = cycle[next_idx]
        if self.set_noise_mode(next_mode):
            return next_mode
        return None

    # ─── Battery ─────────────────────────────────────────────────────────

    def get_battery(self) -> int:
        """Get current battery level."""
        if self._simulate:
            if self.state.battery_level > 5:
                self.state.battery_level = max(5, self.state.battery_level - random.randint(0, 1))
            self._add_log(f"🔋 Battery: {self.state.battery_level}%")
            self._notify()
            return self.state.battery_level

        self._query_battery()
        return self.state.battery_level

    def _query_battery(self):
        """Query battery level from headset."""
        if not self._connection or not self.state.connected:
            return

        frames = self._connection.send_and_receive(OP_BATTERY_GET, timeout=2.0)
        for frame in frames:
            if frame.battery_level is not None:
                self.state.battery_level = frame.battery_level
                self._add_log(f"🔋 Battery: {self.state.battery_level}%")
                break

    # ─── Noise Query ─────────────────────────────────────────────────────

    def _query_noise_mode(self):
        """Query current noise mode from headset."""
        if not self._connection or not self.state.connected:
            return

        frames = self._connection.send_and_receive(OP_NOISE_GET, timeout=2.0)
        for frame in frames:
            if frame.noise_mode is not None:
                self.state.noise_mode = frame.noise_mode
                self._add_log(f"🔇 Current mode: {MODE_NAMES[frame.noise_mode]}")
                break

    # ─── EQ ──────────────────────────────────────────────────────────────

    def set_eq_preset(self, preset: EQPreset) -> bool:
        """Set an EQ preset."""
        self.last_error = None
        p = self.state.profile

        if p.eq_type == EQType.NONE or not p.eq_band_frequencies:
            self.last_error = f"Equalizer is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

        if self._simulate:
            self.state.eq_preset = preset
            num_bands = len(p.eq_band_frequencies)
            if num_bands == 10:
                preset_curves = {
                    EQPreset.FLAT:  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    EQPreset.JAZZ:  [4, 2, 0, 2, -2, -2, 0, 2, 3, 4],
                    EQPreset.VOCAL: [-2, 0, 2, 4, 4, 3, 2, 0, -1, -2],
                    EQPreset.BASS:  [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
                    EQPreset.CLUB:  [4, 3, 2, 0, -2, -2, 0, 2, 3, 4],
                }
                self.state.eq_bands = preset_curves.get(preset, [0] * 10)
            elif num_bands == 5:
                preset_curves = {
                    EQPreset.FLAT:  [0, 0, 0, 0, 0],
                    EQPreset.JAZZ:  [3, 1, -1, 1, 3],
                    EQPreset.VOCAL: [-1, 2, 4, 2, -1],
                    EQPreset.BASS:  [5, 3, 0, 0, 0],
                    EQPreset.CLUB:  [3, 1, -1, 2, 3],
                }
                self.state.eq_bands = preset_curves.get(preset, [0] * 5)
            elif num_bands == 3:
                preset_curves = {
                    EQPreset.FLAT:  [0, 0, 0],
                    EQPreset.JAZZ:  [2, -1, 2],
                    EQPreset.VOCAL: [-2, 3, 0],
                    EQPreset.BASS:  [5, 1, -1],
                    EQPreset.CLUB:  [3, 0, 2],
                }
                self.state.eq_bands = preset_curves.get(preset, [0] * 3)
            else:
                self.state.eq_bands = [0] * num_bands

            self._add_log(f"🎚️ EQ preset → {EQ_PRESET_NAMES.get(preset, 'Custom')}")
            self._notify()
            return True

        if not self.state.connected or not self._connection:
            self.last_error = "Device is not connected."
            self._add_log(f"✗ {self.last_error}")
            return False

        payload = bytes([int(preset.value)])
        success = self._connection.send_command(OP_EQ_SET, payload)
        if success:
            self.state.eq_preset = preset
            self._add_log(f"🎚️ EQ preset → {EQ_PRESET_NAMES.get(preset, 'Custom')}")
            self._notify()
            return True
        else:
            self.last_error = self._connection.last_error or "Failed to send EQ command."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

    def cycle_eq_preset(self) -> Optional[EQPreset]:
        """Cycle through standard EQ presets (Flat -> Jazz -> Vocal -> Bass -> Club)."""
        p = self.state.profile
        if p.eq_type == EQType.NONE or not p.eq_band_frequencies:
            self.last_error = f"Equalizer is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            return None

        cycle = [
            EQPreset.FLAT,
            EQPreset.JAZZ,
            EQPreset.VOCAL,
            EQPreset.BASS,
            EQPreset.CLUB,
        ]
        current_idx = cycle.index(self.state.eq_preset) if self.state.eq_preset in cycle else -1
        next_idx = (current_idx + 1) % len(cycle)
        next_preset = cycle[next_idx]
        if self.set_eq_preset(next_preset):
            return next_preset
        return None

    def set_eq_bands(self, bands: list[int]) -> bool:
        """Set custom EQ band values."""
        self.last_error = None
        p = self.state.profile

        if p.eq_type == EQType.NONE or not p.eq_band_frequencies:
            self.last_error = f"Equalizer is not supported on {p.display_name}."
            self._add_log(f"✗ {self.last_error}")
            return False

        expected = len(p.eq_band_frequencies)
        if len(bands) != expected:
            self.last_error = f"EQ requires exactly {expected} bands for {p.display_name} (got {len(bands)})."
            self._add_log(f"✗ {self.last_error}")
            return False

        bands = [max(-12, min(12, int(b))) for b in bands]

        if self._simulate:
            self.state.eq_bands = bands
            self.state.eq_preset = EQPreset.CUSTOM
            self._add_log(f"🎚️ Custom EQ: {bands}")
            self._notify()
            return True

        if not self.state.connected or not self._connection:
            self.last_error = "Device is not connected."
            self._add_log(f"✗ {self.last_error}")
            return False

        payload = bytes([len(bands)] + [b & 0xFF for b in bands])
        success = self._connection.send_command(OP_EQ_SET, payload)
        if success:
            self.state.eq_bands = bands
            self.state.eq_preset = EQPreset.CUSTOM
            self._add_log(f"🎚️ Custom EQ: {bands}")
            self._notify()
            return True
        else:
            self.last_error = self._connection.last_error or "Failed to send custom EQ command."
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

    def save_eq_to_config(self) -> bool:
        """Persist active EQ preset and band levels to ~/.config/jblpc/config.json."""
        self.last_error = None
        try:
            cfg = load_config()
            cfg["eq_bands"] = list(self.state.eq_bands)
            cfg["eq_preset"] = self.state.eq_preset_name
            save_config(cfg)
            self._add_log(f"💾 Equalizer curve saved to config.json")
            return True
        except Exception as e:
            self.last_error = f"Failed to save EQ configuration: {e}"
            self._add_log(f"✗ {self.last_error}")
            return False

    # ─── Power ───────────────────────────────────────────────────────────

    def power_off(self) -> bool:
        """Power off the headset remotely."""
        self.last_error = None
        p = self.state.profile

        if not p.has_power_off_command:
            self.last_error = (
                f"Remote power-off is not supported on {p.display_name} "
                f"(earbuds power off automatically when placed in charging case)."
            )
            self._add_log(f"✗ {self.last_error}")
            self._notify()
            return False

        if self._simulate:
            self.state.connected = False
            self.state.battery_level = -1
            self._add_log("⚡ Headset powered off (simulation)")
            self._notify()
            return True

        if not self.state.connected or not self._connection:
            self.last_error = "Device is not connected."
            self._add_log(f"✗ {self.last_error}")
            return False

        success = self._connection.send_command(OP_POWER_OFF)
        if success:
            self._add_log("⚡ Power off command sent")
            self.state.connected = False
            self._connection.disconnect()
        else:
            self.last_error = self._connection.last_error or "Failed to send power off command."
            self._add_log(f"✗ {self.last_error}")

        self._notify()
        return success

    # ─── Battery Health Tracking ─────────────────────────────────────────

    def log_health_reading(self, tracker: Optional[BatteryHealthTracker] = None) -> list[str]:
        """Record current battery readings to the health tracker."""
        if tracker is None:
            tracker = BatteryHealthTracker()
        return tracker.log_state(self.state)

    def emit_battery_history(
        self,
        scenario: str = "healthy",
        days: int = 14,
        tracker: Optional[BatteryHealthTracker] = None,
    ) -> BatteryHealthTracker:
        """Scripted battery history generator for simulator testing."""
        if tracker is None:
            tracker = BatteryHealthTracker()
        device_id = self.state.bt_address or self.state.device_name
        generate_synthetic_history(tracker, device_id, scenario=scenario, days=days)
        return tracker

    # ─── Device Info ─────────────────────────────────────────────────────

    def get_status_dict(self) -> dict:
        """Get a dictionary of the current headset or speaker state."""
        return {
            "connected": self.state.connected,
            "simulating": self._simulate,
            "device": self.state.device_name,
            "category": self.state.profile.category.value,
            "battery_scheme": self.state.profile.battery_scheme.value,
            "battery": self.state.battery_level,
            "battery_left": self.state.battery_left,
            "battery_right": self.state.battery_right,
            "battery_case": self.state.battery_case,
            "noise_mode": self.state.noise_mode_name,
            "has_anc": self.state.profile.has_anc,
            "eq_preset": self.state.eq_preset_name,
            "eq_bands": self.state.eq_bands,
            "eq_type": self.state.profile.eq_type.value,
            "firmware": self.state.firmware_version,
            "address": self.state.bt_address,
        }

    # ─── Device Discovery ────────────────────────────────────────────────

    @staticmethod
    def discover_devices() -> list[dict]:
        """Find paired JBL devices."""
        return find_jbl_devices()
