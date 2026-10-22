"""
End-to-End and Component Test Suite for TuneDeck Native GUI.

Executes under headless offscreen mode (QT_QPA_PLATFORM=offscreen).
"""

import os
import time
import pytest

# Ensure headless Qt execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from tunedeck_gui.app import create_application
from tunedeck_gui.bridge import GuiControllerBridge
from tunedeck_gui.windows.main_window import MainWindow
from jblpc.protocol import NoiseMode, EQPreset
from jblpc.lock import SingleInstanceLock


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single persistent QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = create_application()
    return app


@pytest.fixture
def gui_instance(qapp):
    """Create an isolated MainWindow and GuiControllerBridge in simulation mode."""
    bridge = GuiControllerBridge(simulate=True, sim_model="JBL Tune 770NC")
    win = MainWindow(bridge)
    win.show()
    bridge.start()

    # Allow simulation connection to settle
    t0 = time.time()
    while time.time() - t0 < 0.3:
        qapp.processEvents()
        time.sleep(0.02)

    yield win, bridge, qapp

    win.close()
    bridge.disconnect_device()


def test_main_window_components(gui_instance):
    """Verify that all major UI panels, tabs, and status items initialize."""
    win, bridge, qapp = gui_instance

    assert win.device_bar is not None
    assert win.device_spotlight is not None
    assert win.battery_gauge is not None
    assert win.noise_control is not None
    assert win.eq_widget is not None
    assert win.health_panel is not None
    assert win.tabs.count() == 2

    # Check initial model display
    assert win.device_bar.model_combo.currentText() == "JBL Tune 770NC"
    assert bridge.current_profile.display_name == "JBL Tune 770NC"
    assert bridge.current_state.connected is True


def test_noise_mode_switching(gui_instance):
    """Test switching noise cancellation modes via the UI and bridge."""
    win, bridge, qapp = gui_instance

    # Switch to Ambient Aware
    bridge.set_noise_mode(NoiseMode.AMBIENT_AWARE)
    t0 = time.time()
    while time.time() - t0 < 0.3:
        qapp.processEvents()
        time.sleep(0.02)

    assert bridge.current_state.noise_mode == NoiseMode.AMBIENT_AWARE
    assert win.noise_control.active_mode_lbl.text() == "Ambient Aware"

    # Switch to Off
    bridge.set_noise_mode(NoiseMode.OFF)
    t1 = time.time()
    while time.time() - t1 < 0.3:
        qapp.processEvents()
        time.sleep(0.02)

    assert bridge.current_state.noise_mode == NoiseMode.OFF
    assert win.noise_control.active_mode_lbl.text() == "Off"


def test_equalizer_presets_and_sliders(gui_instance):
    """Test applying EQ presets and moving individual band sliders."""
    win, bridge, qapp = gui_instance

    # Set Bass preset
    bridge.set_eq_preset(EQPreset.BASS)
    t0 = time.time()
    while time.time() - t0 < 0.3:
        qapp.processEvents()
        time.sleep(0.02)

    assert bridge.current_state.eq_preset == EQPreset.BASS
    assert win.eq_widget.preset_badge.text() == "Bass Boost"

    # Adjust Band 0 to -4 dB
    win.eq_widget.sliders[0].setValue(-4)
    qapp.processEvents()
    time.sleep(0.1)

    assert win.eq_widget.gain_labels[0].text() == "-4"
    assert win.eq_widget.preset_badge.text() == "Custom"


def test_tws_earbuds_mode_switch(gui_instance):
    """Test switching to a TWS Earbuds model dynamically enables Trio battery dials."""
    win, bridge, qapp = gui_instance

    # Switch to Tune 230NC TWS
    bridge.switch_model("JBL Tune 230NC TWS")
    t0 = time.time()
    while time.time() - t0 < 0.4:
        qapp.processEvents()
        time.sleep(0.02)

    assert bridge.current_profile.display_name == "JBL Tune 230NC TWS"
    assert bridge.current_profile.battery_scheme.value == "tws_trio"

    # Verify UI updated to Trio dials
    assert win.battery_gauge.single_dial.isHidden()
    assert not win.battery_gauge.dial_left.isHidden()
    assert not win.battery_gauge.dial_right.isHidden()
    assert not win.battery_gauge.dial_case.isHidden()


def test_speaker_mode_switch(gui_instance):
    """Test switching to a portable speaker adapts to 3-band EQ and disables ANC."""
    win, bridge, qapp = gui_instance

    # Switch to Flip 6
    bridge.switch_model("JBL Flip 6")
    t0 = time.time()
    while time.time() - t0 < 0.4:
        qapp.processEvents()
        time.sleep(0.02)

    assert bridge.current_profile.display_name == "JBL Flip 6"
    assert bridge.current_profile.has_anc is False
    assert len(bridge.current_profile.eq_band_frequencies) == 3

    # ANC button should be disabled for Flip 6
    anc_btn = win.noise_control.buttons[NoiseMode.ANC]
    assert anc_btn.isEnabled() is False


def test_health_panel_synthetic_data(gui_instance, tmp_path):
    """Test injecting synthetic battery history and updating the Health cards."""
    win, bridge, qapp = gui_instance

    # Switch to temp DB to avoid polluting user DB
    bridge.health_tracker.db_path = tmp_path / "test_health.db"
    bridge.health_tracker._init_db()

    # Generate synthetic history
    bridge.generate_synthetic_history("healthy")
    t0 = time.time()
    while time.time() - t0 < 0.4:
        qapp.processEvents()
        time.sleep(0.02)

    assert win.health_panel.card_efc.val_lbl.text() != "──"
    assert "CONFIDENCE:" in win.health_panel.confidence_badge.text()


def test_cross_platform_lock(tmp_path):
    """Verify SingleInstanceLock functions correctly across platforms."""
    lock_file = tmp_path / "instance.lock"
    lock1 = SingleInstanceLock(lock_dir=tmp_path, name="instance.lock")
    lock1.acquire()
    assert lock_file.exists()

    # Second instance must fail to acquire
    lock2 = SingleInstanceLock(lock_dir=tmp_path, name="instance.lock")
    with pytest.raises(Exception):
        lock2.acquire()

    lock1.release()


def test_bridge_polling_and_connected_property(gui_instance):
    """Verify that bridge controller has connected property and polling runs without error."""
    win, bridge, qapp = gui_instance
    assert bridge.controller.connected is True
    assert bridge.controller.is_connected is True
    assert bridge.controller.state.connected is True

    # Call poll tick directly
    bridge._on_poll_tick()
    t0 = time.time()
    while time.time() - t0 < 0.2:
        qapp.processEvents()
        time.sleep(0.02)

    assert bridge.current_state.battery_level > 0
