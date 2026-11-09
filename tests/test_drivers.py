"""
Unit tests for the pluggable hardware driver architecture (jblpc.drivers).
"""

import pytest
from unittest.mock import MagicMock

from jblpc.drivers import (
    BaseDeviceDriver,
    DriverCapability,
    DriverEvent,
    AirohaRaceDriver,
    JblPortableDriver,
    GenericBtDriver,
    get_driver_for_profile,
)
from jblpc.models import (
    ProtocolFamily,
    DeviceProfile,
    DeviceCategory,
    get_profile_by_id,
)
from jblpc.protocol import (
    NoiseMode,
    EQPreset,
    BluetoothConnection,
)
from jblpc.exceptions import UnsupportedCommandError


def test_driver_factory_resolution():
    """Verify that get_driver_for_profile resolves the correct driver class."""
    tune_profile = get_profile_by_id("tune_770nc")
    flip_profile = get_profile_by_id("flip_6")
    partybox_profile = get_profile_by_id("partybox_310")

    generic_profile = DeviceProfile(
        model_id="generic_headset",
        display_name="Generic BT Headset",
        name_patterns=[],
        category=DeviceCategory.OVER_EAR,
        protocol_family=ProtocolFamily.GENERIC_BT,
    )

    d1 = get_driver_for_profile("AA:BB:CC:DD:EE:01", tune_profile)
    assert isinstance(d1, AirohaRaceDriver)

    d2 = get_driver_for_profile("AA:BB:CC:DD:EE:02", flip_profile)
    assert isinstance(d2, JblPortableDriver)

    d3 = get_driver_for_profile("AA:BB:CC:DD:EE:03", partybox_profile)
    assert isinstance(d3, JblPortableDriver)

    d4 = get_driver_for_profile("AA:BB:CC:DD:EE:04", generic_profile)
    assert isinstance(d4, GenericBtDriver)


def test_driver_capabilities():
    """Verify driver capability flags per silicon family."""
    tune_profile = get_profile_by_id("tune_770nc")
    flip_profile = get_profile_by_id("flip_6")

    d_airoha = get_driver_for_profile("AA:BB:CC:DD:EE:01", tune_profile)
    assert DriverCapability.NOISE_ANC in d_airoha.capabilities
    assert DriverCapability.EQ in d_airoha.capabilities

    d_portable = get_driver_for_profile("AA:BB:CC:DD:EE:02", flip_profile)
    assert DriverCapability.PARTYBOOST in d_portable.capabilities
    assert DriverCapability.NOISE_ANC not in d_portable.capabilities


def test_jbl_portable_driver_stub_safety():
    """JblPortableDriver refuses hardware commands with UnsupportedCommandError."""
    flip_profile = get_profile_by_id("flip_6")
    driver = JblPortableDriver("AA:BB:CC:DD:EE:02", profile=flip_profile)

    assert driver.connected is False
    assert driver.connect() is False
    assert "JBL Portable / PartyBoost" in (driver.last_error or "")

    with pytest.raises(UnsupportedCommandError):
        driver.set_noise_mode(NoiseMode.ANC)

    with pytest.raises(UnsupportedCommandError):
        driver.set_eq_preset(EQPreset.BASS)

    with pytest.raises(UnsupportedCommandError):
        driver.power_off()


def test_generic_bt_driver_safety():
    """GenericBtDriver rejects vendor-specific audio commands."""
    driver = GenericBtDriver("AA:BB:CC:DD:EE:99")

    with pytest.raises(UnsupportedCommandError):
        driver.set_noise_mode(NoiseMode.ANC)

    with pytest.raises(UnsupportedCommandError):
        driver.set_eq_bands([0, 0, 0])

    with pytest.raises(UnsupportedCommandError):
        driver.power_off()


def test_airoha_race_driver_delegation():
    """AirohaRaceDriver delegates socket operations to underlying BluetoothConnection."""
    mock_conn = MagicMock(spec=BluetoothConnection)
    mock_conn.connected = True
    mock_conn.send_command.return_value = True
    mock_conn.receive.return_value = []

    tune_profile = get_profile_by_id("tune_770nc")
    driver = AirohaRaceDriver("AA:BB:CC:DD:EE:01", profile=tune_profile, connection=mock_conn)

    assert driver.connected is True
    assert driver.set_noise_mode(NoiseMode.ANC) is True
    mock_conn.send_command.assert_called_once()


def test_backward_compatibility_imports():
    """Assert all legacy protocol imports in existing tests remain intact."""
    from jblpc.protocol import (
        BluetoothConnection,
        build_request,
        parse_frames,
        Frame,
        OP_NOISE_SET,
        OP_NOISE_GET,
        NoiseMode,
        EQPreset,
    )
    assert BluetoothConnection is not None
    assert callable(build_request)
    assert callable(parse_frames)

