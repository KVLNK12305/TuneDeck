"""
Unit tests for Airoha RACE protocol framing, building, and parsing.
"""

import pytest
import struct
from jblpc.protocol import (
    MAGIC_BYTE,
    FRAME_TYPE_REQUEST,
    FRAME_TYPE_RESPONSE,
    FRAME_TYPE_NOTIFICATION,
    OP_NOISE_SET,
    OP_NOISE_GET,
    OP_BATTERY_GET,
    OP_POWER_OFF,
    NoiseMode,
    build_request,
    parse_frames,
    Frame,
    is_valid_mac,
    ProtocolError,
)


@pytest.mark.protocol
def test_mac_address_validation():
    """Verify MAC address regex validator."""
    assert is_valid_mac("AA:BB:CC:DD:EE:FF")
    assert is_valid_mac("00:11:22:33:44:55")
    assert is_valid_mac("aa-bb-cc-dd-ee-ff")
    assert not is_valid_mac("")
    assert not is_valid_mac("INVALID-MAC")
    assert not is_valid_mac("AA:BB:CC:DD:EE")
    assert not is_valid_mac("AA:BB:CC:DD:EE:FF:00")
    assert not is_valid_mac(12345)


@pytest.mark.protocol
def test_build_request_standard():
    """Build a standard request frame and assert structure."""
    # OP_BATTERY_GET (0x0402) with empty payload
    frame = build_request(OP_BATTERY_GET)
    assert len(frame) == 6
    assert frame[0] == MAGIC_BYTE
    assert frame[1] == FRAME_TYPE_REQUEST
    assert frame[2:4] == struct.pack("<H", 2)  # length = opcode length (2)
    assert frame[4:6] == struct.pack("<H", OP_BATTERY_GET)


@pytest.mark.protocol
def test_build_request_with_payload():
    """Build a request frame with noise control payload."""
    payload = bytes.fromhex("000A01")
    frame = build_request(OP_NOISE_SET, payload)
    assert len(frame) == 6 + len(payload)
    assert frame[2:4] == struct.pack("<H", 2 + len(payload))
    assert frame[6:] == payload


@pytest.mark.protocol
def test_parse_single_frame():
    """Parse a valid response frame."""
    # 05 5B 03 00 02 04 55 (battery response: 85%)
    raw = bytes([0x05, FRAME_TYPE_RESPONSE, 0x03, 0x00, 0x02, 0x04, 0x55])
    frames, remaining = parse_frames(raw)
    assert len(frames) == 1
    assert remaining == b""
    f = frames[0]
    assert f.frame_type == FRAME_TYPE_RESPONSE
    assert f.opcode == OP_BATTERY_GET
    assert f.payload == bytes([0x55])
    assert f.battery_level == 85


@pytest.mark.protocol
def test_parse_noise_mode_response():
    """Parse noise mode get response."""
    # 05 5B 06 00 01 09 00 00 00 01 (ANC mode)
    raw = bytes([0x05, FRAME_TYPE_RESPONSE, 0x06, 0x00, 0x01, 0x09, 0x00, 0x00, 0x00, 0x01])
    frames, remaining = parse_frames(raw)
    assert len(frames) == 1
    assert frames[0].noise_mode == NoiseMode.ANC


@pytest.mark.protocol
def test_parse_multiple_frames():
    """Parse multiple concatenated frames."""
    f1 = bytes([0x05, FRAME_TYPE_RESPONSE, 0x03, 0x00, 0x02, 0x04, 0x50])
    f2 = bytes([0x05, FRAME_TYPE_NOTIFICATION, 0x03, 0x00, 0x02, 0x04, 0x4F])
    frames, remaining = parse_frames(f1 + f2)
    assert len(frames) == 2
    assert remaining == b""
    assert frames[0].battery_level == 80
    assert frames[1].battery_level == 79


@pytest.mark.protocol
def test_parse_truncated_frames():
    """Truncated frames are retained in the remaining buffer without error."""
    # Incomplete header (< 4 bytes)
    frames, remaining = parse_frames(b"\x05\x5B")
    assert frames == []
    assert remaining == b"\x05\x5B"

    # Header indicates 10 bytes payload, but only 3 available
    partial = bytes([0x05, FRAME_TYPE_RESPONSE, 0x0A, 0x00, 0x02, 0x04, 0x11])
    frames, remaining = parse_frames(partial)
    assert frames == []
    assert remaining == partial


@pytest.mark.protocol
def test_parse_garbage_bytes_recovery():
    """Garbage bytes before magic byte are safely discarded."""
    garbage = b"\xDE\xAD\xBE\xEF\x12\x34"
    valid = bytes([0x05, FRAME_TYPE_RESPONSE, 0x03, 0x00, 0x02, 0x04, 0x60])
    frames, remaining = parse_frames(garbage + valid)
    assert len(frames) == 1
    assert frames[0].battery_level == 96
    assert remaining == b""


@pytest.mark.protocol
def test_parse_oversized_frame():
    """Oversized frame lengths are rejected to prevent memory exhaustion."""
    # Length claimed is 65000 (0xFDE8)
    oversized = bytes([0x05, FRAME_TYPE_RESPONSE, 0xE8, 0xFD, 0x02, 0x04])
    frames, remaining = parse_frames(oversized)
    assert frames == []


@pytest.mark.protocol
def test_parse_noise_mode_notification_and_response_formats():
    """Verify parsing real hardware unsolicited notification and query response frames."""
    from jblpc.protocol import (
        FRAME_TYPE_NOTIFICATION,
        OP_NOISE_SET,
        OP_NOISE_GET,
        OP_BATTERY_PERCENTAGE,
        get_system_battery_level,
    )
    # 1. Real hardware notification: 05 5C 06 00 01 09 05 00 00 01 (ANC)
    anc_ntf = bytes([0x05, FRAME_TYPE_NOTIFICATION, 0x06, 0x00, 0x01, 0x09, 0x05, 0x00, 0x00, 0x01])
    f_anc, _ = parse_frames(anc_ntf)
    assert len(f_anc) == 1
    assert f_anc[0].noise_mode == NoiseMode.ANC

    # 2. Real hardware notification: 05 5C 06 00 01 09 05 00 00 00 (OFF)
    off_ntf = bytes([0x05, FRAME_TYPE_NOTIFICATION, 0x06, 0x00, 0x01, 0x09, 0x05, 0x00, 0x00, 0x00])
    f_off, _ = parse_frames(off_ntf)
    assert len(f_off) == 1
    assert f_off[0].noise_mode == NoiseMode.OFF

    # 3. Real hardware notification: Ambient Aware (0x0A) and TalkThru (0x09)
    amb_ntf = bytes([0x05, FRAME_TYPE_NOTIFICATION, 0x06, 0x00, 0x01, 0x09, 0x05, 0x00, 0x00, 0x0A])
    f_amb, _ = parse_frames(amb_ntf)
    assert f_amb[0].noise_mode == NoiseMode.AMBIENT_AWARE

    talk_ntf = bytes([0x05, FRAME_TYPE_NOTIFICATION, 0x06, 0x00, 0x01, 0x09, 0x05, 0x00, 0x00, 0x09])
    f_talk, _ = parse_frames(talk_ntf)
    assert f_talk[0].noise_mode == NoiseMode.TALKTHRU

    # 4. Battery percentage reading 0x0403 (e.g. 100%)
    batt_frame = bytes([0x05, FRAME_TYPE_RESPONSE, 0x0A, 0x00, 0x03, 0x04, 0x03, 0x00, 0x00, 0x03, 0x00, 0x00, 0x5D, 0x64])
    f_batt, _ = parse_frames(batt_frame)
    assert len(f_batt) == 1
    assert f_batt[0].battery_level == 100

    # 5. Invalid / empty MAC check for get_system_battery_level
    assert get_system_battery_level("") is None
    assert get_system_battery_level("invalid-mac") is None

