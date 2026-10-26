"""
Tests for companion-app-level dynamic device detection and strict UI capability gating.
"""

import subprocess
import pytest
from unittest.mock import patch, MagicMock

from jblpc.protocol import (
    find_jbl_devices,
    get_active_jbl_device,
    is_harman_jbl_info,
    is_jbl_device_name,
    NoiseMode,
)
from jblpc.models import (
    get_profile_by_id,
    match_device_profile,
    EQType,
)
from jblpc.controller import HeadsetController
from jblpc.tui.app import JBLPcApp, NoiseControlWidget, EQWidget


class TestDynamicDeviceDetection:
    """Validate companion-app-level dynamic Bluetooth detection without hardcoded MACs."""

    def test_harman_vendor_id_signature_detection(self):
        """Even if the user renamed the device to 'Office Audio', Harman's SIG ID 0x0057 identifies it as JBL."""
        fake_info = (
            "Device 11:22:33:44:55:66 (public)\n"
            "\tName: JBL Tune 770NC\n"
            "\tAlias: Office Audio\n"
            "\tConnected: yes\n"
            "\tModalias: bluetooth:v0057p20B7d0100\n"
            "\tUUID: Vendor specific (5052494d-2dab-0341-6972-6f6861424c45)\n"
        )
        is_jbl, name = is_harman_jbl_info(fake_info)
        assert is_jbl is True
        assert "770NC" in name

    def test_non_harman_device_ignored(self):
        """Other bluetooth headsets (Sony, OnePlus, Bose) should not be detected as JBL."""
        fake_info = (
            "Device 99:88:77:66:55:44 (public)\n"
            "\tName: Sony WH-1000XM4\n"
            "\tAlias: My Headphones\n"
            "\tConnected: yes\n"
            "\tModalias: bluetooth:v004Cp1234d0100\n"
        )
        is_jbl, name = is_harman_jbl_info(fake_info)
        assert is_jbl is False

    def test_vendor_ids(self):
        """Only Harman's Bluetooth SIG IDs match; 0x0ECB is assigned to a different company."""
        for vid, expected in [("0057", True), ("075A", True), ("0ECB", False)]:
            info = f"Device 11:22:33:44:55:66\n\tAlias: Desk\n\tModalias: bluetooth:v{vid}p2050d0100\n"
            assert is_harman_jbl_info(info)[0] is expected, vid

    def test_generic_product_words_are_not_jbl(self):
        """Names like 'Live Audio' or 'Car Charger' must not be treated as JBL devices."""
        assert is_jbl_device_name("JBL Tune 770NC")
        assert is_jbl_device_name("jbl flip 6")
        for name in ["Live Audio", "Car Charger", "Club Speaker", "Galaxy Buds Live", "Tour Bus 770"]:
            assert not is_jbl_device_name(name)

    @patch("jblpc.protocol.check_bluetoothctl_available")
    @patch("subprocess.run")
    def test_active_connected_device_takes_precedence(self, mock_run, mock_check):
        """A currently connected JBL device takes precedence over any previously saved device."""
        def run_router(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            if cmd == ["bluetoothctl", "devices", "Connected"]:
                mock.stdout = b"Device CC:DD:EE:FF:00:11 JBL Flip 6\n"
            elif cmd == ["bluetoothctl", "devices"]:
                mock.stdout = b"Device AA:BB:CC:DD:EE:FF JBL Tune 770NC\nDevice CC:DD:EE:FF:00:11 JBL Flip 6\n"
            elif len(cmd) >= 3 and cmd[1] == "info":
                mock.stdout = b"Device CC:DD:EE:FF:00:11\n\tName: JBL Flip 6\n\tConnected: yes\n\tModalias: bluetooth:v0057p1234\n"
            else:
                mock.stdout = b""
            return mock

        mock_run.side_effect = run_router

        active = get_active_jbl_device()
        assert active is not None
        assert active["address"] == "CC:DD:EE:FF:00:11"
        assert active["name"] == "JBL Flip 6"
        assert active["connected"] is True


class TestModelCapabilityGating:
    """Validate that only compatible options are displayed and actionable for each model."""

    @pytest.mark.asyncio
    async def test_non_anc_model_gating(self):
        """Models without ANC (like Flip 6) must hide noise mode buttons."""
        ctrl = HeadsetController(simulate=True, model="flip_6")
        app = JBLPcApp(ctrl)

        async with app.run_test() as pilot:
            noise_w = app.query_one(NoiseControlWidget)
            noise_buttons = app.query_one("#noise-buttons")
            unsupported = app.query_one("#noise-unsupported")

            assert noise_buttons.display is False
            assert unsupported.display is True

            # Triggering noise keybindings on non-anc model must be guarded
            app.action_noise_anc()
            assert ctrl.state.noise_mode == NoiseMode.OFF

    @pytest.mark.asyncio
    async def test_anc_only_model_gating(self):
        """Models with ANC but no Ambient/TalkThru (Tune 760NC) must hide Ambient & Talk buttons."""
        ctrl = HeadsetController(simulate=True, model="tune_760nc")
        app = JBLPcApp(ctrl)

        async with app.run_test() as pilot:
            btn_off = app.query_one("#noise-off")
            btn_anc = app.query_one("#noise-anc")
            btn_ambient = app.query_one("#noise-ambient")
            btn_talk = app.query_one("#noise-talk")

            assert btn_off.display is True
            assert btn_anc.display is True
            assert btn_ambient.display is False
            assert btn_talk.display is False

    @pytest.mark.asyncio
    async def test_tws_earbuds_poweroff_hidden(self):
        """TWS earbuds power off automatically in the case; remote power-off button must be hidden."""
        ctrl = HeadsetController(simulate=True, model="tune_230nc_tws")
        app = JBLPcApp(ctrl)

        async with app.run_test() as pilot:
            btn_power = app.query_one("#btn-poweroff")
            assert btn_power.display is False

            # Calling action_power_off directly must also guard
            app.action_power_off()
            # Still connected in simulator because command is not supported on earbuds
            assert ctrl.state.connected is True

    @pytest.mark.asyncio
    async def test_speaker_3_band_eq_gating(self):
        """Speakers with 3-band EQ must show exactly 3 sliders and hide the remaining 7."""
        ctrl = HeadsetController(simulate=True, model="charge_5")
        app = JBLPcApp(ctrl)

        async with app.run_test() as pilot:
            eq_w = app.query_one(EQWidget)
            assert len(eq_w.bands) == 10
            for i in range(3):
                assert eq_w.bands[i].display is True
            for i in range(3, 10):
                assert eq_w.bands[i].display is False

    @pytest.mark.asyncio
    async def test_non_eq_model_gating(self):
        """Models without EQ (Tune 510BT) must hide sliders and presets completely."""
        ctrl = HeadsetController(simulate=True, model="tune_510bt")
        app = JBLPcApp(ctrl)

        async with app.run_test() as pilot:
            bands_c = app.query_one("#eq-bands-container")
            presets_box = app.query_one("#eq-preset-buttons")
            unsupported = app.query_one("#eq-unsupported")

            assert bands_c.display is False
            assert presets_box.display is False
            assert unsupported.display is True


class TestHardwareScope:
    """Hardware paths only claim what is implemented."""

    @patch("jblpc.controller.check_device_connected", return_value=True)
    @patch("jblpc.controller.check_device_paired", return_value=True)
    @patch("jblpc.controller.check_bluetooth_adapter_powered")
    @patch("jblpc.controller.find_jbl_devices", return_value=[])
    @patch("jblpc.controller.get_active_jbl_device", return_value=None)
    def test_speaker_hardware_control_not_implemented(
        self, _active, _find, _adapter, _paired, _connected, isolated_env
    ):
        """Speakers use a non-RACE protocol; connecting must fail with a clear message, not send RACE frames."""
        from tests.conftest import FakeRFCOMMSocket, FakeBluetoothConnection

        fake_sock = FakeRFCOMMSocket()
        conn = FakeBluetoothConnection("AA:BB:CC:DD:EE:FF", fake_socket=fake_sock)
        ctrl = HeadsetController(bt_address="AA:BB:CC:DD:EE:FF", model_id="flip_6", connection=conn)
        assert ctrl.connect() is False
        assert "not implemented" in ctrl.last_error
        assert fake_sock.sent_data == []

    def test_tws_hardware_shows_single_level(self, isolated_env):
        """On hardware only an overall level is read, so TWS displays fall back to it."""
        ctrl = HeadsetController(bt_address="", model_id="tune_230nc_tws")
        assert ctrl.state.shows_tws_trio is True  # nothing known yet
        ctrl.state.battery_level = 80
        assert ctrl.state.shows_tws_trio is False
        ctrl.state.battery_left = 70
        assert ctrl.state.shows_tws_trio is True

    @patch("jblpc.controller.check_bluetooth_adapter_powered")
    @patch("jblpc.controller.find_jbl_devices", return_value=[])
    @patch("jblpc.controller.get_active_jbl_device", return_value=None)
    def test_no_rfcomm_platform_fails_fast(self, _active, _find, adapter_check, isolated_env, monkeypatch):
        """On macOS (no RFCOMM sockets) connect fails immediately with a clear message, before slow system probes."""
        import socket
        import sys

        monkeypatch.delattr(socket, "AF_BLUETOOTH", raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        ctrl = HeadsetController(bt_address="AA:BB:CC:DD:EE:FF", model_id="tune_770nc")
        assert ctrl.connect() is False
        assert "macOS" in ctrl.last_error and "--sim" in ctrl.last_error
        adapter_check.assert_not_called()
