"""
Thread-safe controller bridge for TuneDeck GUI.

Connects PySide6 event loop to the underlying HeadsetController and SQLite
BatteryHealthTracker without blocking the UI thread.
"""

import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from jblpc.controller import HeadsetController, HeadsetState
from jblpc.protocol import NoiseMode, EQPreset, save_config, load_config
from jblpc.models import (
    DeviceProfile,
    SUPPORTED_MODELS,
    match_device_profile,
    get_profile_by_id,
)
from jblpc.health import DeviceHealthReport, BatteryHealthTracker, generate_synthetic_history
from jblpc.exceptions import (
    BluetoothAdapterError,
    DeviceNotPairedError,
    ConnectionError as JBLConnectionError,
    UnsupportedCommandError,
)


class ControllerSignals(QObject):
    """Signals emitted by the controller bridge."""
    state_updated = Signal(object)              # HeadsetState
    health_updated = Signal(object)             # DeviceHealthReport
    connection_changed = Signal(bool, str)      # is_connected, message
    error_occurred = Signal(str)                # error string
    power_off_completed = Signal()              # notification of power-off


class GuiControllerBridge(QObject):
    """
    Coordinates headset actions, background polling, and Qt signal emissions.
    """
    _req_start_poll = Signal(int)
    _req_stop_poll = Signal()

    def __init__(
        self,
        simulate: bool = True,
        sim_model: str = "JBL Tune 770NC",
        address: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.simulate = simulate
        self.sim_model = sim_model
        self.address = address
        self.signals = ControllerSignals()

        self._controller: Optional[HeadsetController] = None
        self.health_tracker = BatteryHealthTracker()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_tick)
        self._req_start_poll.connect(self._poll_timer.start)
        self._req_stop_poll.connect(self._poll_timer.stop)
        self._lock = threading.RLock()

    @property
    def controller(self) -> HeadsetController:
        with self._lock:
            if self._controller is None:
                addr = self.address or ""
                if not addr and not self.simulate:
                    try:
                        from jblpc.protocol import load_config, save_config, get_active_jbl_device
                        active_dev = get_active_jbl_device()
                        if active_dev and active_dev.get("address"):
                            addr = active_dev["address"]
                            if active_dev.get("connected"):
                                cfg = load_config()
                                cfg["bluetooth_address"] = addr
                                save_config(cfg)
                            if not self.sim_model and active_dev.get("name"):
                                from jblpc.models import match_device_profile
                                matched = match_device_profile(active_dev["name"])
                                if matched:
                                    self.sim_model = matched.display_name
                        if not addr:
                            cfg = load_config()
                            addr = cfg.get("bluetooth_address", "")
                    except Exception as err:
                        pass_err = str(err)
                self._controller = HeadsetController(
                    bt_address=addr,
                    simulate=self.simulate,
                    model=self.sim_model,
                )
            return self._controller

    @property
    def current_state(self) -> HeadsetState:
        return self.controller.state

    @property
    def current_profile(self) -> DeviceProfile:
        return self.controller.state.profile

    def start(self, auto_connect: bool = True):
        """Initialize controller and attempt connection."""
        if auto_connect:
            self.connect_device()

    def connect_device(self):
        """Initiate connection in a worker thread."""
        def _worker():
            try:
                success = self.controller.connect()
                if success:
                    self.signals.connection_changed.emit(True, "Connected")
                    self.signals.state_updated.emit(self.controller.state)
                    self._update_health()
                    self._start_polling()
                else:
                    err = self.controller.last_error or "Connection failed."
                    self.signals.connection_changed.emit(False, err)
            except Exception as e:
                self.signals.connection_changed.emit(False, str(e))
                self.signals.error_occurred.emit(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def disconnect_device(self):
        """Disconnect and stop polling."""
        self._stop_polling()
        def _worker():
            try:
                self.controller.disconnect()
                self.signals.connection_changed.emit(False, "Disconnected")
                self.signals.state_updated.emit(self.controller.state)
            except Exception as e:
                self.signals.error_occurred.emit(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def switch_model(self, model_name: str):
        """Switch device model profile (in simulation mode)."""
        def _worker():
            with self._lock:
                self._stop_polling()
                self.sim_model = model_name
                self._controller = HeadsetController(
                    bt_address=self.address or "",
                    simulate=self.simulate,
                    model=model_name,
                )
                self._controller.connect()
                self.signals.connection_changed.emit(True, f"Loaded {model_name}")
                self.signals.state_updated.emit(self._controller.state)
                self._update_health()
                self._start_polling()

        threading.Thread(target=_worker, daemon=True).start()

    def set_simulation_mode(self, enabled: bool):
        """Toggle between hardware connection and simulator."""
        if self.simulate == enabled:
            return
        def _worker():
            with self._lock:
                self._stop_polling()
                if self._controller:
                    self._controller.disconnect()
                self.simulate = enabled
                self._controller = HeadsetController(
                    bt_address=self.address or "",
                    simulate=self.simulate,
                    model=self.sim_model,
                )
                self._controller.connect()
                mode_str = "Simulator Mode" if enabled else "Hardware Mode"
                self.signals.connection_changed.emit(True, f"Switched to {mode_str}")
                self.signals.state_updated.emit(self._controller.state)
                self._update_health()
                self._start_polling()

        threading.Thread(target=_worker, daemon=True).start()

    def set_noise_mode(self, mode: NoiseMode):
        """Change noise control mode."""
        def _worker():
            try:
                self.controller.set_noise_mode(mode)
                self.signals.state_updated.emit(self.controller.state)
            except UnsupportedCommandError as e:
                self.signals.error_occurred.emit(str(e))
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to set noise mode: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def set_eq_preset(self, preset: EQPreset):
        """Apply EQ preset."""
        def _worker():
            try:
                self.controller.set_eq_preset(preset)
                self.signals.state_updated.emit(self.controller.state)
            except UnsupportedCommandError as e:
                self.signals.error_occurred.emit(str(e))
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to set EQ preset: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def set_eq_band(self, band_idx: int, gain_db: int):
        """Adjust a specific EQ band gain."""
        def _worker():
            try:
                bands = list(self.controller.state.eq_bands)
                if 0 <= band_idx < len(bands):
                    bands[band_idx] = max(-12, min(12, gain_db))
                    self.controller.set_eq_bands(bands)
                    self.signals.state_updated.emit(self.controller.state)
            except UnsupportedCommandError as e:
                self.signals.error_occurred.emit(str(e))
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to set EQ band: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def set_all_eq_bands(self, bands: list[int]):
        """Set all band gains simultaneously."""
        def _worker():
            try:
                self.controller.set_eq_bands(bands)
                self.signals.state_updated.emit(self.controller.state)
            except UnsupportedCommandError as e:
                self.signals.error_occurred.emit(str(e))
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to set EQ bands: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def save_eq_to_config(self):
        """Persist active EQ preset and band levels to config file."""
        def _worker():
            try:
                cfg = load_config()
                cfg["eq_preset"] = int(self.controller.state.eq_preset)
                cfg["eq_bands"] = list(self.controller.state.eq_bands)
                save_config(cfg)
                self.signals.state_updated.emit(self.controller.state)
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to save EQ config: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def power_off(self):
        """Execute remote power off command."""
        def _worker():
            try:
                self.controller.power_off()
                self._stop_polling()
                self.signals.power_off_completed.emit()
                self.signals.connection_changed.emit(False, "Device Powered Off")
                self.signals.state_updated.emit(self.controller.state)
            except UnsupportedCommandError as e:
                self.signals.error_occurred.emit(str(e))
            except Exception as e:
                self.signals.error_occurred.emit(f"Power off failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def generate_synthetic_history(self, scenario: str = "healthy"):
        """Populate database with synthetic battery history for visualization."""
        def _worker():
            try:
                device_id = self.controller.state.bt_address or self.controller.state.device_name
                generate_synthetic_history(self.health_tracker, device_id, scenario=scenario, days=14)
                self._update_health()
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to generate synthetic data: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _start_polling(self, interval_ms: int = 4000):
        self._req_start_poll.emit(interval_ms)

    def _stop_polling(self):
        self._req_stop_poll.emit()

    def _on_poll_tick(self):
        """Periodic telemetry polling on the timer."""
        if not self.controller.state.connected:
            return
        def _worker():
            try:
                self.controller.poll_battery()
                self.signals.state_updated.emit(self.controller.state)
                self._update_health()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _update_health(self):
        """Derive latest health report and emit signal."""
        try:
            device_id = self.controller.state.bt_address or self.controller.state.device_name
            self.health_tracker.log_state(self.controller.state)
            report = self.health_tracker.get_health_summary(device_id, self.controller.state.device_name)
            self.signals.health_updated.emit(report)
        except Exception:
            pass
