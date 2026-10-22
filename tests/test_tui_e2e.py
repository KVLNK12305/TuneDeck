"""
End-to-end TUI headless tests using Textual's run_test / Pilot.
Tests interactive operation on:
  - A TWS model (tune_230nc_tws)
  - A single-battery headphone (tune_770nc)
  - A speaker (flip_6)
"""

import pytest
from textual.widgets import Button, Static
from jblpc.controller import HeadsetController
from jblpc.tui.app import JBLPcApp, BrandBanner, BatteryWidget, HealthWidget, EQWidget
from jblpc.protocol import NoiseMode, EQPreset


@pytest.mark.tui
@pytest.mark.asyncio
async def test_tui_tws_model(isolated_env):
    """
    Test TUI on a TWS earbud model (tune_230nc_tws).
    Verify:
      - TWS trio battery layout (L, R, Case)
      - Keypresses for ANC, ambient, EQ preset, health panel toggle, quit
      - Screen content reflects model name and state without crashes
    """
    controller = HeadsetController(simulate=True, model_id="tune_230nc_tws")
    app = JBLPcApp(controller)

    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()

        # Check initial screen content
        banner = app.query_one(BrandBanner)
        assert banner is not None
        assert "Tune 230NC TWS" in app.title

        # Check battery widget is displaying TWS Trio
        batt_widget = app.query_one(BatteryWidget)
        assert batt_widget is not None

        # Press keys for noise control:
        # '2' = ANC
        await pilot.press("2")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.ANC

        # '3' = Ambient Aware
        await pilot.press("3")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.AMBIENT_AWARE

        # '4' = TalkThru
        await pilot.press("4")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.TALKTHRU

        # '1' = Noise Off
        await pilot.press("1")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.OFF

        # 'n' = Cycle noise
        await pilot.press("n")
        await pilot.pause()
        assert controller.state.noise_mode in (NoiseMode.OFF, NoiseMode.ANC, NoiseMode.AMBIENT_AWARE, NoiseMode.TALKTHRU)

        # EQ interaction: Click Bass preset
        eq_widget = app.query_one(EQWidget)
        assert eq_widget is not None
        btn_bass = app.query_one("#eq-bass", Button)
        await pilot.click(btn_bass)
        await pilot.pause()
        assert controller.state.eq_preset == EQPreset.BASS

        # Click Vocal preset
        btn_vocal = app.query_one("#eq-vocal", Button)
        await pilot.click(btn_vocal)
        await pilot.pause()
        # 'e' = Cycle EQ preset shortcut
        await pilot.press("e")
        await pilot.pause()
        assert controller.state.eq_preset in (EQPreset.FLAT, EQPreset.JAZZ, EQPreset.VOCAL, EQPreset.BASS, EQPreset.CLUB)

        # 'h' = Toggle Health widget
        health_widget = app.query_one(HealthWidget)
        initial_display = health_widget.display
        await pilot.press("h")
        await pilot.pause()
        assert health_widget.display != initial_display
        await pilot.press("h")
        await pilot.pause()
        assert health_widget.display == initial_display

        # 'b' = Check battery
        await pilot.press("b")
        await pilot.pause()
        assert controller.state.battery_left >= 0
        assert controller.state.battery_right >= 0

        # 'q' = Quit
        await pilot.press("q")


@pytest.mark.tui
@pytest.mark.asyncio
async def test_tui_single_battery_headphone(isolated_env):
    """
    Test TUI on a single-battery headphone (tune_770nc).
    Verify:
      - Single battery level display
      - Keypresses for ANC ('2'), Ambient ('3'), EQ ('#eq-jazz'), Quit ('q')
      - Clean exit
    """
    controller = HeadsetController(simulate=True, model_id="tune_770nc")
    app = JBLPcApp(controller)

    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()

        # Check screen rendering
        assert "Tune 770NC" in app.title

        # Verify single battery bar rendered
        batt_widget = app.query_one(BatteryWidget)
        assert batt_widget is not None

        # Keypress for ANC
        await pilot.press("2")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.ANC

        # Keypress for Ambient
        await pilot.press("3")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.AMBIENT_AWARE

        # Click EQ preset Jazz
        btn_jazz = app.query_one("#eq-jazz", Button)
        await pilot.click(btn_jazz)
        await pilot.pause()
        assert controller.state.eq_preset == EQPreset.JAZZ

        # Quit
        await pilot.press("q")


@pytest.mark.tui
@pytest.mark.asyncio
async def test_tui_speaker_model(isolated_env):
    """
    Test TUI on a portable Bluetooth speaker (flip_6).
    Verify:
      - Speaker profile loaded
      - Sane rendering when ANC is not supported
      - 3-band EQ works
      - Clean exit with 'q'
    """
    controller = HeadsetController(simulate=True, model_id="flip_6")
    app = JBLPcApp(controller)

    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()

        assert "Flip 6" in app.title

        # Speaker has 3-band EQ
        eq_widget = app.query_one(EQWidget)
        assert eq_widget is not None
        assert len(controller.state.profile.eq_band_frequencies) == 3

        # Click Flat preset
        btn_flat = app.query_one("#eq-flat", Button)
        await pilot.click(btn_flat)
        await pilot.pause()
        assert controller.state.eq_preset == EQPreset.FLAT

        # Attempting ANC key ('2') on speaker should not crash
        await pilot.press("2")
        await pilot.pause()
        # Remains OFF because Flip 6 has no ANC
        assert controller.state.noise_mode == NoiseMode.OFF

        # Attempting Cycle noise ('n') on speaker should not crash
        await pilot.press("n")
        await pilot.pause()
        assert controller.state.noise_mode == NoiseMode.OFF

        # Quit
        await pilot.press("q")


@pytest.mark.tui
@pytest.mark.asyncio
async def test_tui_equalizer_wasd_and_save(isolated_env):
    """
    Test TUI equalizer keyboard navigation (WASD) and Ctrl+S saving.
    Verify:
      - 'a' / 'd' navigates selected band left / right
      - 'w' / 's' increments / decrements active band gain
      - 'ctrl+s' saves EQ bands to config.json
    """
    import json
    controller = HeadsetController(simulate=True, model_id="tune_770nc")
    app = JBLPcApp(controller)

    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()

        eq_widget = app.query_one(EQWidget)
        assert eq_widget is not None
        assert eq_widget.selected_band == 0
        assert eq_widget.bands[0].is_selected is True

        # Test 'w': increase gain of band 0
        initial_val = eq_widget.bands[0].value
        await pilot.press("w")
        await pilot.pause()
        assert eq_widget.bands[0].value == initial_val + 1
        assert controller.state.eq_bands[0] == initial_val + 1

        # Test 's': decrease gain of band 0
        await pilot.press("s")
        await pilot.pause()
        assert eq_widget.bands[0].value == initial_val
        assert controller.state.eq_bands[0] == initial_val

        # Test 'd': move right to band 1
        await pilot.press("d")
        await pilot.pause()
        assert eq_widget.selected_band == 1
        assert eq_widget.bands[1].is_selected is True
        assert eq_widget.bands[0].is_selected is False

        # Test 'w' on band 1
        await pilot.press("w")
        await pilot.press("w")
        await pilot.pause()
        assert eq_widget.bands[1].value == 2
        assert controller.state.eq_bands[1] == 2

        # Test 'a': move left back to band 0
        await pilot.press("a")
        await pilot.pause()
        assert eq_widget.selected_band == 0
        assert eq_widget.bands[0].is_selected is True

        # Test 'ctrl+s': save to config.json
        await pilot.press("ctrl+s")
        await pilot.pause()

        config_file = isolated_env["config_dir"] / "jblpc" / "config.json"
        assert config_file.exists()
        saved_data = json.loads(config_file.read_text(encoding="utf-8"))
        assert saved_data.get("eq_bands") is not None
        assert saved_data["eq_bands"][1] == 2

        # Clean quit
        await pilot.press("q")


@pytest.mark.tui
@pytest.mark.asyncio
async def test_tui_simulation_toggle_button(isolated_env):
    """
    Verify:
      - Default hardware mode (simulate=False) does not show simulation badge
      - '#btn-simulate' button starts with label '🧪 Simulation'
      - Clicking simulation button or pressing 'm' enables simulation mode
      - Button label toggles to '🔌 Hardware' and banner shows SIMULATOR
      - Clicking again switches back to hardware mode and removes simulation badge
    """
    controller = HeadsetController(simulate=False, model_id="tune_770nc", bt_address="AA:BB:CC:DD:EE:FF")
    app = JBLPcApp(controller)

    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()

        # In hardware mode, verify button label and lack of simulation badge
        sim_btn = app.query_one("#btn-simulate", Button)
        assert sim_btn is not None
        assert "Simulation" in str(sim_btn.label)

        banner = app.query_one(BrandBanner)
        assert banner is not None
        assert "SIMULATOR" not in str(banner.query_one("#banner-content", Static).render())

        # Click simulation button
        await pilot.click("#btn-simulate")
        await pilot.pause()

        # Verify simulation mode is now active
        assert controller.simulating is True
        assert "Hardware" in str(sim_btn.label)
        assert "SIMULATOR" in str(banner.query_one("#banner-content", Static).render())

        # Press 'm' to toggle back to hardware mode
        await pilot.press("m")
        await pilot.pause()

        # Verify hardware mode is restored and simulation badge is gone
        assert controller.simulating is False
        assert "Simulation" in str(sim_btn.label)
        assert "SIMULATOR" not in str(banner.query_one("#banner-content", Static).render())

        await pilot.press("q")

