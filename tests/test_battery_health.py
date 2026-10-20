"""
Tests for battery health tracking, equivalent full cycle (EFC) estimation,
discharge rate derivation, retention trend, confidence scoring, and synthetic history generation.
"""

import time
import pytest
from pathlib import Path
from jblpc.health import (
    BatteryHealthTracker,
    generate_synthetic_history,
    ComponentHealth,
    DeviceHealthReport,
)
from jblpc.controller import HeadsetController, HeadsetState
from jblpc.models import get_profile_by_id


@pytest.mark.health
def test_battery_tracker_basic_logging(isolated_env):
    """Test logging single and multi-component readings to SQLite."""
    db_file = isolated_env["data_dir"] / "test_health.db"
    tracker = BatteryHealthTracker(db_path=db_file)

    now = time.time()
    # Valid readings
    assert tracker.log_reading("dev1", "single", 85, charging_state=0, timestamp=now) is True
    assert tracker.log_reading("dev1", "single", 80, charging_state=0, timestamp=now + 1800) is True

    # Invalid percentage readings must be rejected
    assert tracker.log_reading("dev1", "single", -5, charging_state=0) is False
    assert tracker.log_reading("dev1", "single", 105, charging_state=0) is False

    # Check components
    comps = tracker.get_components_for_device("dev1")
    assert comps == ["single"]


@pytest.mark.health
def test_battery_tracker_tws_logging(isolated_env):
    """Test logging TWS earbuds trio components (left, right, case)."""
    db_file = isolated_env["data_dir"] / "test_health_tws.db"
    tracker = BatteryHealthTracker(db_path=db_file)

    profile = get_profile_by_id("tune_230nc_tws")
    state = HeadsetState(
        bt_address="11:22:33:44:55:66",
        device_name="JBL Tune 230NC TWS",
        profile=profile,
        battery_left=90,
        battery_right=85,
        battery_case=100,
    )

    logged = tracker.log_state(state)
    assert bool(logged) is True
    assert "left" in logged and "right" in logged and "case" in logged

    comps = sorted(tracker.get_components_for_device("11:22:33:44:55:66"))
    assert comps == ["case", "left", "right"]


@pytest.mark.health
def test_synthetic_scenario_healthy(isolated_env):
    """
    Test healthy synthetic scenario:
      - 14 days of regular use
      - High confidence
      - Non-zero equivalent full cycles
      - Normal discharge rate (~5%/hr)
      - Retention trend near 100%
    """
    db_file = isolated_env["data_dir"] / "health_healthy.db"
    tracker = BatteryHealthTracker(db_path=db_file)
    device_id = "test_dev_healthy"

    generate_synthetic_history(tracker, device_id, scenario="healthy", days=14)

    health = tracker.get_component_health(device_id, "single")
    assert health.readings_count > 30
    assert health.data_span_days >= 13.0
    assert health.confidence == "high"
    assert health.estimated_cycles > 1.0  # Several cycles completed
    assert health.discharge_rate_pct_per_hr is not None
    assert 3.0 <= health.discharge_rate_pct_per_hr <= 8.0  # Near 5%/hr
    assert health.retention_trend_pct is not None
    assert 85.0 <= health.retention_trend_pct <= 115.0  # Stable retention
    assert "Estimated metric" in health.note


@pytest.mark.health
def test_synthetic_scenario_degraded(isolated_env):
    """
    Test degraded synthetic scenario:
      - Discharge rate doubles in second half
      - Retention trend shows noticeable drop (< 90%)
    """
    db_file = isolated_env["data_dir"] / "health_degraded.db"
    tracker = BatteryHealthTracker(db_path=db_file)
    device_id = "test_dev_degraded"

    generate_synthetic_history(tracker, device_id, scenario="degraded", days=14)

    health = tracker.get_component_health(device_id, "single")
    assert health.confidence == "high"
    assert health.discharge_rate_pct_per_hr is not None
    assert health.retention_trend_pct is not None
    # Degraded discharge rate makes retention ratio drop significantly
    assert health.retention_trend_pct < 90.0


@pytest.mark.health
def test_synthetic_scenario_gaps(isolated_env):
    """
    Test multi-day tracking gaps:
      - Tracker must not crash
      - Gaps must not produce absurd discharge rates
    """
    db_file = isolated_env["data_dir"] / "health_gaps.db"
    tracker = BatteryHealthTracker(db_path=db_file)
    device_id = "test_dev_gaps"

    generate_synthetic_history(tracker, device_id, scenario="gaps", days=14)

    health = tracker.get_component_health(device_id, "single")
    assert health.readings_count > 10
    # Discharge rate should still be reasonable and not distorted by the multi-day gap
    if health.discharge_rate_pct_per_hr:
        assert health.discharge_rate_pct_per_hr < 25.0


@pytest.mark.health
def test_synthetic_scenario_clock_jumps(isolated_env):
    """Test out-of-order timestamps; database time-sorting must prevent negative durations."""
    db_file = isolated_env["data_dir"] / "health_jumps.db"
    tracker = BatteryHealthTracker(db_path=db_file)
    device_id = "test_dev_jumps"

    generate_synthetic_history(tracker, device_id, scenario="clock_jumps", days=14)

    health = tracker.get_component_health(device_id, "single")
    assert health.readings_count > 20
    assert health.estimated_cycles >= 0.0


@pytest.mark.health
def test_synthetic_scenario_duplicate_rows(isolated_env):
    """Test duplicate sensor logs; must be deduplicated or handled smoothly."""
    db_file = isolated_env["data_dir"] / "health_duplicates.db"
    tracker = BatteryHealthTracker(db_path=db_file)
    device_id = "test_dev_dups"

    generate_synthetic_history(tracker, device_id, scenario="duplicate_rows", days=14)

    health = tracker.get_component_health(device_id, "single")
    assert health.readings_count > 20
    assert health.estimated_cycles > 0.0


@pytest.mark.health
def test_corrupt_database_handling(isolated_env):
    """Test handling of corrupted SQLite database file."""
    db_file = isolated_env["data_dir"] / "corrupt_health.db"
    # Write garbage non-sqlite content
    db_file.write_bytes(b"NOT A SQLITE DATABASE GARBAGE DATA 1234567890")

    # Creating tracker must auto-heal by backing up corrupt DB and creating fresh schema
    tracker = BatteryHealthTracker(db_path=db_file)
    assert tracker.log_reading("dev1", "single", 80) is True

    health = tracker.get_component_health("dev1", "single")
    assert health.current_level == 80
    assert health.confidence == "low"


@pytest.mark.health
def test_simulator_emit_battery_history(isolated_env):
    """Test simulator emit_battery_history method directly on HeadsetController."""
    controller = HeadsetController(simulate=True, model_id="tune_770nc")
    tracker = controller.emit_battery_history(scenario="healthy", days=7)

    report = tracker.get_health_summary(controller.state.device_name)
    assert "single" in report.components
    comp = report.components["single"]
    assert comp.readings_count > 10
    assert comp.confidence in ("medium", "high")


@pytest.mark.health
def test_confidence_tiers(isolated_env):
    """Test confidence scoring progression: low -> medium -> high."""
    db_file = isolated_env["data_dir"] / "health_tiers.db"
    tracker = BatteryHealthTracker(db_path=db_file)
    dev = "tier_test"
    now = time.time()

    # Tier 1: Low confidence (< 10 readings or < 1 day)
    tracker.log_reading(dev, "single", 100, timestamp=now)
    tracker.log_reading(dev, "single", 95, timestamp=now + 1800)
    h1 = tracker.get_component_health(dev, "single")
    assert h1.confidence == "low"
    assert "Insufficient data" in h1.note

    # Tier 2: Medium confidence (10-30 readings or 1-7 days)
    for i in range(15):
        tracker.log_reading(dev, "single", 90 - (i % 5), timestamp=now + (i * 7200))
    h2 = tracker.get_component_health(dev, "single")
    assert h2.confidence == "medium"
    assert "days of observation" in h2.note
