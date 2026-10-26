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


DEFAULT_SIM_MODEL = "JBL Tune 770NC"


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
        sim_model: Optional[str] = DEFAULT_SIM_MODEL,
        address: Optional[str] = None,
        parent: Optional[QObject] = None,
        hw_model: Optional[str] = None,
    ):
        super().__init__(parent)
        self.simulate = simulate
        self.sim_model = sim_model or DEFAULT_SIM_MODEL
        self.hw_model = hw_model
        self.address = address
        self.signals = ControllerSignals()

        self._controller: Optional[HeadsetController] = None
        self.health_tracker = BatteryHealthTracker()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_tick)
        self._req_start_poll.connect(self._poll_timer.start)
        self._req_stop_poll.connect(self._poll_timer.stop)
        self._lock = threading.RLock()
        self._workers: list[threading.Thread] = []

    def _spawn(self, target):
        """Run target on a worker thread that shutdown() can wait for."""
        t = threading.Thread(target=target, daemon=True)
        with self._lock:
            self._workers = [w for w in self._workers if w.is_alive()]
            self._workers.append(t)
        t.start()

    def shutdown(self, timeout: float = 3.0):
        """Stop polling and wait for in-flight workers, so none emit into destroyed Qt objects."""
        self._poll_timer.stop()
        with self._lock:
            workers = list(self._workers)
        for t in workers:
            t.join(timeout)

    @property
    def controller(self) -> HeadsetController:
        with self._lock:
            if self._controller is None:
                self._controller = self._new_controller()
            return self._controller

    def _new_controller(self) -> HeadsetController:
        """Build a controller for the current mode."""
        if self.simulate:
            return HeadsetController(
                bt_address="",
                simulate=True,
                model=self.sim_model or DEFAULT_SIM_MODEL,
            )
        # Hardware: an explicit address wins; otherwise bt_address=None lets the
        # controller discover the connected/paired JBL device and pick the profile
        # from its broadcast name (unless the user chose a model with --model).
        return HeadsetController(
            bt_address=self.address or None,
            simulate=False,
            model=self.hw_model,
        )

    def _connect_and_report(self, ok_message: str = "Connected"):
        """Connect the current controller and report the real outcome to the UI."""
        controller = self.controller
        success = controller.connect()
        if success:
            if not self.simulate and controller.state.bt_address:
                self._remember_address(controller.state.bt_address)
            self.signals.connection_changed.emit(True, ok_message)
            self._update_health()
            self._start_polling()
        else:
            self.signals.connection_changed.emit(False, controller.last_error or "Connection failed.")
        self.signals.state_updated.emit(controller.state)
        return success

    @staticmethod
    def _remember_address(address: str):
        """Persist a working hardware address so the next launch connects straight away."""
        try:
            cfg = load_config()
            if cfg.get("bluetooth_address") != address:
                cfg["bluetooth_address"] = address
                save_config(cfg)
        except Exception:
            pass  # Remembering the address is a convenience only

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
                self._connect_and_report()
            except Exception as e:
                self.signals.connection_changed.emit(False, str(e))
                self.signals.error_occurred.emit(str(e))

        self._spawn(_worker)

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

        self._spawn(_worker)

    def switch_model(self, model_name: str):
        """Switch device model profile (in simulation mode)."""
        def _worker():
            with self._lock:
                self._stop_polling()
                if self._controller:
                    self._controller.disconnect()
                self.sim_model = model_name
                if not self.simulate:
                    self.hw_model = model_name  # user override of the detected profile
                self._controller = self._new_controller()
                self._connect_and_report(f"Loaded {model_name}")

        self._spawn(_worker)

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
                self._controller = self._new_controller()
                mode_str = "Simulator Mode" if enabled else "Hardware Mode"
                self._connect_and_report(f"Switched to {mode_str}")

        self._spawn(_worker)

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

        self._spawn(_worker)

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

        self._spawn(_worker)

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

        self._spawn(_worker)

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

        self._spawn(_worker)

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

        self._spawn(_worker)

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

        self._spawn(_worker)

    def generate_synthetic_history(self, scenario: str = "healthy"):
        """Populate database with synthetic battery history for visualization."""
        def _worker():
            try:
                device_id = self.controller.state.bt_address or self.controller.state.device_name
                generate_synthetic_history(self.health_tracker, device_id, scenario=scenario, days=14)
                self._update_health()
            except Exception as e:
                self.signals.error_occurred.emit(f"Failed to generate synthetic data: {e}")

        self._spawn(_worker)

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

        self._spawn(_worker)

    def _update_health(self):
        """Derive latest health report and emit signal."""
        try:
            device_id = self.controller.state.bt_address or self.controller.state.device_name
            self.health_tracker.log_state(self.controller.state)
            report = self.health_tracker.get_health_summary(device_id, self.controller.state.device_name)
            self.signals.health_updated.emit(report)
        except Exception:
            pass
