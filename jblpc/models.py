"""
Device profile registry and model definitions for JBL devices.

Capability profiles for JBL devices (Tune, Live, Tour, Club, Wave/Vibe TWS,
and portable speakers), matched by broadcast name. Profiles drive which
controls the UI shows; they are compiled from public product specs, not
tested against each model. Hardware control is only implemented for the
Airoha RACE protocol family; speaker/PartyBox profiles work in --sim only.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Optional


class DeviceCategory(Enum):
    OVER_EAR = "Over-Ear / On-Ear Headphones"
    TWS = "True Wireless Earbuds (TWS)"
    SPEAKER = "Portable Speaker"
    PARTYBOX = "PartyBox High-Power Speaker"
    UNKNOWN = "Generic JBL Device"


class ProtocolFamily(Enum):
    AIROHA_RACE = "Airoha RACE (RFCOMM 21)"
    JBL_PORTABLE = "JBL Portable / PartyBoost"
    PARTYBOX = "JBL PartyBox"
    QUANTUM = "JBL Quantum Gaming"


class BatteryScheme(Enum):
    SINGLE = "single"          # Standard single battery %
    TWS_TRIO = "tws_trio"      # Left bud, Right bud, Charging case
    SPEAKER = "speaker"        # Speaker battery + AC charging status


class EQType(Enum):
    NONE = "none"
    SPEAKER_3_BAND = "3_band"         # Bass, Mid, Treble (-6 to +6 dB)
    PARAMETRIC_5_BAND = "5_band"      # 5-band graphic/parametric EQ
    PARAMETRIC_10_BAND = "10_band"    # 10-band full EQ (Tune/Live/Tour)


@dataclass
class DeviceProfile:
    """Defines capabilities, protocol specs, and audio controls for a JBL model."""
    model_id: str
    display_name: str
    name_patterns: list[str]
    category: DeviceCategory = DeviceCategory.OVER_EAR
    protocol_family: ProtocolFamily = ProtocolFamily.AIROHA_RACE
    rfcomm_channel: int = 21

    # Audio & Noise features
    has_anc: bool = True
    has_ambient_aware: bool = True
    has_talkthru: bool = True
    has_spatial_audio: bool = False

    # EQ Configuration
    eq_type: EQType = EQType.PARAMETRIC_10_BAND
    eq_presets: list[str] = field(default_factory=lambda: [
        "Flat", "Jazz", "Vocal", "Bass Boost", "Club", "Custom"
    ])
    eq_band_frequencies: list[str] = field(default_factory=lambda: [
        "32Hz", "64Hz", "125Hz", "250Hz", "500Hz",
        "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"
    ])

    # Power & Battery
    battery_scheme: BatteryScheme = BatteryScheme.SINGLE
    has_power_off_command: bool = True
    has_auto_off_timer: bool = True

    # Speaker specific
    has_partyboost: bool = False
    has_auracast: bool = False
    has_lightshow: bool = False

    def matches_name(self, device_name: str) -> bool:
        """Check if a Bluetooth broadcast name matches this model."""
        clean_name = device_name.strip()
        for pat in self.name_patterns:
            if re.search(pat, clean_name, re.IGNORECASE):
                return True
        return False


# ─── Pre-configured Device Catalog ──────────────────────────────────────────

SUPPORTED_MODELS: list[DeviceProfile] = [
    # ─── Tune Series (Over-Ear) ───
    DeviceProfile(
        model_id="tune_770nc",
        display_name="JBL Tune 770NC",
        name_patterns=[r"JBL\s*TUNE\s*770NC", r"TUNE\s*770NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_760nc",
        display_name="JBL Tune 760NC",
        name_patterns=[r"JBL\s*TUNE\s*760NC", r"TUNE\s*760NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_720bt",
        display_name="JBL Tune 720BT",
        name_patterns=[r"JBL\s*TUNE\s*720BT", r"TUNE\s*720BT"],
        category=DeviceCategory.OVER_EAR,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_710bt",
        display_name="JBL Tune 710BT",
        name_patterns=[r"JBL\s*TUNE\s*710BT", r"TUNE\s*710BT"],
        category=DeviceCategory.OVER_EAR,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_670nc",
        display_name="JBL Tune 670NC",
        name_patterns=[r"JBL\s*TUNE\s*670NC", r"TUNE\s*670NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_660nc",
        display_name="JBL Tune 660NC",
        name_patterns=[r"JBL\s*TUNE\s*660NC", r"TUNE\s*660NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_520bt",
        display_name="JBL Tune 520BT",
        name_patterns=[r"JBL\s*TUNE\s*520BT", r"TUNE\s*520BT"],
        category=DeviceCategory.OVER_EAR,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="tune_510bt",
        display_name="JBL Tune 510BT",
        name_patterns=[r"JBL\s*TUNE\s*510BT", r"TUNE\s*510BT"],
        category=DeviceCategory.OVER_EAR,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.NONE,
        eq_band_frequencies=[],
        eq_presets=[],
    ),

    # ─── Live Series (Premium Over-Ear) ───
    DeviceProfile(
        model_id="live_770nc",
        display_name="JBL Live 770NC",
        name_patterns=[r"JBL\s*LIVE\s*770NC", r"LIVE\s*770NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        has_spatial_audio=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="live_670nc",
        display_name="JBL Live 670NC",
        name_patterns=[r"JBL\s*LIVE\s*670NC", r"LIVE\s*670NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        has_spatial_audio=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="live_660nc",
        display_name="JBL Live 660NC",
        name_patterns=[r"JBL\s*LIVE\s*660NC", r"LIVE\s*660NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),
    DeviceProfile(
        model_id="live_460nc",
        display_name="JBL Live 460NC",
        name_patterns=[r"JBL\s*LIVE\s*460NC", r"LIVE\s*460NC"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),

    # ─── Tour Series (Flagship Over-Ear) ───
    DeviceProfile(
        model_id="tour_one_m2",
        display_name="JBL Tour One M2",
        name_patterns=[r"JBL\s*TOUR\s*ONE\s*M2", r"TOUR\s*ONE\s*M2", r"JBL\s*TOUR\s*ONE"],
        category=DeviceCategory.OVER_EAR,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        has_spatial_audio=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
    ),

    # ─── True Wireless Earbuds (TWS) ───
    DeviceProfile(
        model_id="tune_230nc_tws",
        display_name="JBL Tune 230NC TWS",
        name_patterns=[r"JBL\s*TUNE\s*230NC", r"TUNE\s*230NC"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_5_BAND,
        eq_band_frequencies=["64Hz", "250Hz", "1kHz", "4kHz", "16kHz"],
        has_power_off_command=False,  # Earbuds turn off in case
    ),
    DeviceProfile(
        model_id="tune_130nc_tws",
        display_name="JBL Tune 130NC TWS",
        name_patterns=[r"JBL\s*TUNE\s*130NC", r"TUNE\s*130NC"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_5_BAND,
        eq_band_frequencies=["64Hz", "250Hz", "1kHz", "4kHz", "16kHz"],
        has_power_off_command=False,
    ),
    DeviceProfile(
        model_id="tune_beam",
        display_name="JBL Tune Beam",
        name_patterns=[r"JBL\s*TUNE\s*BEAM", r"TUNE\s*BEAM"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_5_BAND,
        eq_band_frequencies=["64Hz", "250Hz", "1kHz", "4kHz", "16kHz"],
        has_power_off_command=False,
    ),
    DeviceProfile(
        model_id="tune_flex",
        display_name="JBL Tune Flex",
        name_patterns=[r"JBL\s*TUNE\s*FLEX", r"TUNE\s*FLEX"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_5_BAND,
        eq_band_frequencies=["64Hz", "250Hz", "1kHz", "4kHz", "16kHz"],
        has_power_off_command=False,
    ),
    DeviceProfile(
        model_id="live_pro_2_tws",
        display_name="JBL Live Pro 2 TWS",
        name_patterns=[r"JBL\s*LIVE\s*PRO\s*2", r"LIVE\s*PRO\s*2"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        has_spatial_audio=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
        has_power_off_command=False,
    ),
    DeviceProfile(
        model_id="tour_pro_2",
        display_name="JBL Tour Pro 2",
        name_patterns=[r"JBL\s*TOUR\s*PRO\s*2", r"TOUR\s*PRO\s*2"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=True,
        has_ambient_aware=True,
        has_talkthru=True,
        has_spatial_audio=True,
        eq_type=EQType.PARAMETRIC_10_BAND,
        has_power_off_command=False,
    ),
    DeviceProfile(
        model_id="wave_buds",
        display_name="JBL Wave / Vibe Buds",
        name_patterns=[r"JBL\s*WAVE\s*BUDS", r"JBL\s*VIBE\s*BUDS", r"WAVE\s*BUDS"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=False,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_5_BAND,
        eq_band_frequencies=["64Hz", "250Hz", "1kHz", "4kHz", "16kHz"],
        has_power_off_command=False,
    ),
    DeviceProfile(
        model_id="endurance_peak_3",
        display_name="JBL Endurance Peak 3",
        name_patterns=[r"JBL\s*ENDURANCE\s*PEAK", r"ENDURANCE\s*PEAK"],
        category=DeviceCategory.TWS,
        battery_scheme=BatteryScheme.TWS_TRIO,
        has_anc=False,
        has_ambient_aware=True,
        has_talkthru=True,
        eq_type=EQType.PARAMETRIC_5_BAND,
        eq_band_frequencies=["64Hz", "250Hz", "1kHz", "4kHz", "16kHz"],
        has_power_off_command=False,
    ),

    # ─── Portable Speakers (Flip, Charge, Xtreme, Boombox) ───
    DeviceProfile(
        model_id="flip_6",
        display_name="JBL Flip 6",
        name_patterns=[r"JBL\s*FLIP\s*6", r"FLIP\s*6"],
        category=DeviceCategory.SPEAKER,
        protocol_family=ProtocolFamily.JBL_PORTABLE,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        eq_presets=["Standard", "Bass Boost", "Voice", "Custom"],
        has_partyboost=True,
    ),
    DeviceProfile(
        model_id="charge_5",
        display_name="JBL Charge 5",
        name_patterns=[r"JBL\s*CHARGE\s*5", r"CHARGE\s*5"],
        category=DeviceCategory.SPEAKER,
        protocol_family=ProtocolFamily.JBL_PORTABLE,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        eq_presets=["Standard", "Bass Boost", "Voice", "Custom"],
        has_partyboost=True,
    ),
    DeviceProfile(
        model_id="xtreme_4",
        display_name="JBL Xtreme 4",
        name_patterns=[r"JBL\s*XTREME\s*4", r"XTREME\s*4"],
        category=DeviceCategory.SPEAKER,
        protocol_family=ProtocolFamily.JBL_PORTABLE,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        eq_presets=["Standard", "Bass Boost", "Voice", "Custom"],
        has_partyboost=True,
        has_auracast=True,
    ),
    DeviceProfile(
        model_id="boombox_3",
        display_name="JBL Boombox 3",
        name_patterns=[r"JBL\s*BOOMBOX\s*3", r"BOOMBOX\s*3"],
        category=DeviceCategory.SPEAKER,
        protocol_family=ProtocolFamily.JBL_PORTABLE,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        eq_presets=["Standard", "Bass Boost", "Voice", "Custom"],
        has_partyboost=True,
    ),
    DeviceProfile(
        model_id="pulse_5",
        display_name="JBL Pulse 5",
        name_patterns=[r"JBL\s*PULSE\s*5", r"PULSE\s*5"],
        category=DeviceCategory.SPEAKER,
        protocol_family=ProtocolFamily.JBL_PORTABLE,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        has_partyboost=True,
        has_lightshow=True,
    ),

    # ─── PartyBox Series ───
    DeviceProfile(
        model_id="partybox_310",
        display_name="JBL PartyBox 310",
        name_patterns=[r"JBL\s*PARTYBOX\s*310", r"PARTYBOX\s*310"],
        category=DeviceCategory.PARTYBOX,
        protocol_family=ProtocolFamily.PARTYBOX,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        has_lightshow=True,
    ),
    DeviceProfile(
        model_id="partybox_110",
        display_name="JBL PartyBox 110",
        name_patterns=[r"JBL\s*PARTYBOX\s*110", r"PARTYBOX\s*110"],
        category=DeviceCategory.PARTYBOX,
        protocol_family=ProtocolFamily.PARTYBOX,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        has_lightshow=True,
    ),
    DeviceProfile(
        model_id="partybox_stage_320",
        display_name="JBL PartyBox Stage 320",
        name_patterns=[r"JBL\s*PARTYBOX\s*STAGE\s*320", r"PARTYBOX\s*STAGE\s*320", r"STAGE\s*320"],
        category=DeviceCategory.PARTYBOX,
        protocol_family=ProtocolFamily.PARTYBOX,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        has_auracast=True,
        has_lightshow=True,
    ),
    DeviceProfile(
        model_id="partybox_club_120",
        display_name="JBL PartyBox Club 120",
        name_patterns=[r"JBL\s*PARTYBOX\s*CLUB\s*120", r"PARTYBOX\s*CLUB\s*120", r"CLUB\s*120"],
        category=DeviceCategory.PARTYBOX,
        protocol_family=ProtocolFamily.PARTYBOX,
        has_anc=False,
        has_ambient_aware=False,
        has_talkthru=False,
        eq_type=EQType.SPEAKER_3_BAND,
        eq_band_frequencies=["Bass", "Mid", "Treble"],
        has_auracast=True,
        has_lightshow=True,
    ),
]

# ─── Fallback Profiles for Unrecognized Models ──────────────────────────────

GENERIC_HEADPHONES = DeviceProfile(
    model_id="generic_jbl_headphones",
    display_name="Generic JBL Headphones",
    name_patterns=[r"JBL.*(TUNE|LIVE|TOUR|CLUB|HEADPHONES|BT|NC)"],
    category=DeviceCategory.OVER_EAR,
    protocol_family=ProtocolFamily.AIROHA_RACE,
    has_anc=True,
    has_ambient_aware=True,
    has_talkthru=True,
    eq_type=EQType.PARAMETRIC_10_BAND,
)

GENERIC_TWS = DeviceProfile(
    model_id="generic_jbl_tws",
    display_name="Generic JBL TWS Earbuds",
    name_patterns=[r"JBL.*(TWS|BUDS|BEAM|FLEX|WAVE|VIBE|PEAK)"],
    category=DeviceCategory.TWS,
    protocol_family=ProtocolFamily.AIROHA_RACE,
    battery_scheme=BatteryScheme.TWS_TRIO,
    has_anc=True,
    has_ambient_aware=True,
    has_talkthru=True,
    eq_type=EQType.PARAMETRIC_5_BAND,
    has_power_off_command=False,
)

GENERIC_SPEAKER = DeviceProfile(
    model_id="generic_jbl_speaker",
    display_name="Generic JBL Speaker",
    name_patterns=[r"JBL.*(FLIP|CHARGE|XTREME|BOOMBOX|CLIP|GO|PULSE|PARTYBOX)"],
    category=DeviceCategory.SPEAKER,
    protocol_family=ProtocolFamily.JBL_PORTABLE,
    has_anc=False,
    has_ambient_aware=False,
    has_talkthru=False,
    eq_type=EQType.SPEAKER_3_BAND,
    has_partyboost=True,
)


def get_profile_by_id(model_id: str) -> Optional[DeviceProfile]:
    """Retrieve a device profile by its unique model_id."""
    for model in SUPPORTED_MODELS:
        if model.model_id.lower() == model_id.lower():
            return model
    return None


def match_device_profile(device_name: str) -> DeviceProfile:
    """
    Intelligently match a Bluetooth device broadcast name to a known profile,
    or fall back to a reasonable generic profile.
    """
    # 1. Exact catalog search
    for model in SUPPORTED_MODELS:
        if model.matches_name(device_name):
            return model

    # 2. Generic heuristics
    name_upper = device_name.upper()
    if any(k in name_upper for k in ["TWS", "BUDS", "BEAM", "FLEX", "WAVE", "VIBE", "EARBUDS"]):
        return GENERIC_TWS
    if any(k in name_upper for k in ["FLIP", "CHARGE", "XTREME", "BOOMBOX", "CLIP", "GO", "PULSE", "SPEAKER", "PARTYBOX"]):
        return GENERIC_SPEAKER
    if "JBL" in name_upper:
        return GENERIC_HEADPHONES

    # Default to Tune 770NC if completely unknown
    return SUPPORTED_MODELS[0]


def list_supported_models() -> list[DeviceProfile]:
    """Return list of all explicitly cataloged JBL models."""
    return list(SUPPORTED_MODELS)
