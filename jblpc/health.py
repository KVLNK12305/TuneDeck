"""
Battery health tracking, cycle estimation, and retention trend analysis.

Since JBL devices do not expose hardware cycle counters or fuel-gauge wear
registers over Bluetooth, this module tracks timestamped battery levels in a
local SQLite database and derives:
  - Estimated Equivalent Full Cycles (sum of upward charge movements / 100)
  - Active Discharge Rate (% per hour)
  - Retention Trend (discharge efficiency compared to baseline recording window)
  - Explicit confidence levels ('low', 'medium', 'high')
"""

import os
import sys
import sqlite3
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Union
from .exceptions import JBLPcError


def get_data_dir() -> Path:
    """Get the data directory for TuneDeck / JBLPc across platforms."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = Path(xdg_data)
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        base = Path(localappdata) if localappdata else (Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    tunedeck_dir = base / "tunedeck"
    jblpc_dir = base / "jblpc"
    if tunedeck_dir.exists() and (tunedeck_dir / "health.db").exists():
        return tunedeck_dir
    data_dir = jblpc_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir



DEFAULT_DB_PATH = get_data_dir() / "health.db"


@dataclass
class ComponentHealth:
    component: str  # 'single', 'left', 'right', 'case'
    current_level: int
    charging_state: int
    readings_count: int
    data_span_days: float
    estimated_cycles: float
    discharge_rate_pct_per_hr: Optional[float]
    retention_trend_pct: Optional[float]
    confidence: str  # 'low', 'medium', 'high'
    note: str


@dataclass
class DeviceHealthReport:
    device_id: str
    device_name: str
    timestamp: float
    components: dict[str, ComponentHealth]


class BatteryHealthTracker:
    """Tracks battery history and estimates health/retention metrics."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            self.db_path = get_data_dir() / "health.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Open a database connection with timeout and foreign keys."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS battery_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        device_id TEXT NOT NULL,
                        component TEXT NOT NULL,
                        percent INTEGER NOT NULL,
                        charging_state INTEGER NOT NULL DEFAULT 0
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_dev_comp_time
                    ON battery_readings(device_id, component, timestamp);
                """)
        except sqlite3.DatabaseError as e:
            # Corrupted DB: isolate corrupted file and recreate clean database
            try:
                if self.db_path.exists():
                    backup = self.db_path.with_suffix(f".db.corrupt.{int(time.time())}")
                    self.db_path.rename(backup)
                with self._get_connection() as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS battery_readings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp REAL NOT NULL,
                            device_id TEXT NOT NULL,
                            component TEXT NOT NULL,
                            percent INTEGER NOT NULL,
                            charging_state INTEGER NOT NULL DEFAULT 0
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_dev_comp_time
                        ON battery_readings(device_id, component, timestamp);
                    """)
            except (sqlite3.DatabaseError, OSError) as err:
                raise JBLPcError(f"Database error initializing battery health database: {err}") from err

    def log_reading(
        self,
        device_id: str,
        component: str,
        percent: int,
        charging_state: int = 0,
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        Record a single battery reading.
        Returns True if recorded, False on invalid values or error.
        """
        if percent < 0 or percent > 100:
            return False

        if timestamp is None:
            timestamp = time.time()

        try:
            with self._get_connection() as conn:
                # Avoid exact duplicate readings within 2 seconds
                cur = conn.cursor()
                cur.execute("""
                    SELECT id FROM battery_readings
                    WHERE device_id = ? AND component = ? AND timestamp >= ? AND percent = ?
                    LIMIT 1
                """, (device_id, component, timestamp - 2.0, percent))
                if cur.fetchone():
                    return True  # Deduplicated

                conn.execute("""
                    INSERT INTO battery_readings (timestamp, device_id, component, percent, charging_state)
                    VALUES (?, ?, ?, ?, ?)
                """, (timestamp, device_id, component, percent, int(charging_state)))
            return True
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error logging battery reading: {e}") from e

    def log_state(self, state, timestamp: Optional[float] = None) -> list[str]:
        """Record readings from a HeadsetState object for all its components."""
        device_id = state.bt_address or state.device_name
        logged = []

        if getattr(state.profile, "battery_scheme", None) and state.profile.battery_scheme.value == "tws_trio":
            if state.battery_left >= 0:
                self.log_reading(device_id, "left", state.battery_left, 0, timestamp)
                logged.append("left")
            if state.battery_right >= 0:
                self.log_reading(device_id, "right", state.battery_right, 0, timestamp)
                logged.append("right")
            if state.battery_case >= 0:
                self.log_reading(device_id, "case", state.battery_case, 0, timestamp)
                logged.append("case")
        else:
            if state.battery_level >= 0:
                self.log_reading(device_id, "single", state.battery_level, 0, timestamp)
                logged.append("single")

        return logged

    def get_readings(
        self,
        device_id: str,
        component: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Fetch chronological readings for a device component."""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT timestamp, percent, charging_state
                    FROM battery_readings
                    WHERE device_id = ? AND component = ?
                    ORDER BY timestamp ASC
                """
                if limit:
                    query += f" LIMIT {int(limit)}"
                rows = conn.execute(query, (device_id, component)).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error reading battery health data: {e}") from e

    def get_components_for_device(self, device_id: str) -> list[str]:
        """Return list of distinct components recorded for a device."""
        try:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT DISTINCT component FROM battery_readings
                    WHERE device_id = ?
                    ORDER BY component ASC
                """, (device_id,)).fetchall()
                return [r["component"] for r in rows]
        except sqlite3.DatabaseError as e:
            raise RuntimeError(f"Database error reading components: {e}") from e

    def get_component_health(self, device_id: str, component: str) -> ComponentHealth:
        """Derive battery health metrics for a component."""
        readings = self.get_readings(device_id, component)

        if not readings:
            return ComponentHealth(
                component=component,
                current_level=-1,
                charging_state=0,
                readings_count=0,
                data_span_days=0.0,
                estimated_cycles=0.0,
                discharge_rate_pct_per_hr=None,
                retention_trend_pct=None,
                confidence="low",
                note="No battery log history recorded yet.",
            )

        # Handle clock jumps by re-sorting by timestamp
        readings = sorted(readings, key=lambda r: r["timestamp"])

        last_reading = readings[-1]
        current_level = last_reading["percent"]
        charging_state = last_reading["charging_state"]
        count = len(readings)

        first_ts = readings[0]["timestamp"]
        last_ts = readings[-1]["timestamp"]
        span_seconds = max(0.0, last_ts - first_ts)
        span_days = span_seconds / 86400.0

        # 1. Equivalent Full Cycles: Sum of upward charge movement / 100
        upward_movement = 0.0
        discharge_deltas = []  # (pct_drop, hours)

        for i in range(1, len(readings)):
            prev = readings[i - 1]
            curr = readings[i]
            dt_hours = (curr["timestamp"] - prev["timestamp"]) / 3600.0

            # Ignore backwards clock anomalies or zero dt
            if dt_hours <= 0:
                continue

            delta = curr["percent"] - prev["percent"]
            if delta > 0:
                upward_movement += delta
            elif delta < 0:
                # Valid active discharge window (between 30 seconds and 8 hours)
                if 0.008 <= dt_hours <= 8.0 and prev["charging_state"] == 0:
                    pct_drop = abs(delta)
                    discharge_deltas.append((pct_drop, dt_hours, curr["timestamp"]))

        estimated_cycles = round(upward_movement / 100.0, 2)

        # 2. Average Discharge Rate (%/hour)
        total_drop = sum(d[0] for d in discharge_deltas)
        total_hours = sum(d[1] for d in discharge_deltas)

        discharge_rate = None
        if total_hours >= 0.2 and total_drop > 0:
            discharge_rate = round(total_drop / total_hours, 2)

        # 3. Retention Trend (discharge rate in recent period vs baseline)
        retention_trend = None
        if span_days >= 3.0 and len(discharge_deltas) >= 6:
            midpoint_ts = first_ts + (span_seconds / 2.0)
            early = [d for d in discharge_deltas if d[2] <= midpoint_ts]
            recent = [d for d in discharge_deltas if d[2] > midpoint_ts]

            early_drop = sum(d[0] for d in early)
            early_hrs = sum(d[1] for d in early)
            recent_drop = sum(d[0] for d in recent)
            recent_hrs = sum(d[1] for d in recent)

            if early_hrs >= 0.2 and recent_hrs >= 0.2 and early_drop > 0 and recent_drop > 0:
                early_rate = early_drop / early_hrs
                recent_rate = recent_drop / recent_hrs
                # Higher recent rate = faster discharge = lower retention
                ratio = (early_rate / recent_rate) * 100.0
                retention_trend = round(min(120.0, max(40.0, ratio)), 1)

        # 4. Confidence & Note
        if count < 10 or span_days < 1.0 or total_hours < 1.0:
            confidence = "low"
            note = "Estimated metric. Insufficient data: at least 24 hours of active use needed for reliable baseline."
        elif count < 30 or span_days < 7.0:
            confidence = "medium"
            note = f"Estimated metric based on {span_days:.1f} days of observation. Confidence will increase with longer usage."
        else:
            confidence = "high"
            note = f"Estimated metric based on {span_days:.1f} days ({count} samples) of consistent monitoring."

        return ComponentHealth(
            component=component,
            current_level=current_level,
            charging_state=charging_state,
            readings_count=count,
            data_span_days=round(span_days, 1),
            estimated_cycles=estimated_cycles,
            discharge_rate_pct_per_hr=discharge_rate,
            retention_trend_pct=retention_trend,
            confidence=confidence,
            note=note,
        )

    def get_health_summary(self, device_id: str, device_name: str = "") -> DeviceHealthReport:
        """Generate a complete health summary for all recorded components of a device."""
        components = self.get_components_for_device(device_id)
        if not components:
            components = ["single"]

        comp_dict = {}
        for c in components:
            comp_dict[c] = self.get_component_health(device_id, c)

        return DeviceHealthReport(
            device_id=device_id,
            device_name=device_name or device_id,
            timestamp=time.time(),
            components=comp_dict,
        )


def generate_synthetic_history(
    tracker: BatteryHealthTracker,
    device_id: str,
    scenario: str = "healthy",
    days: int = 14,
):
    """
    Populates synthetic battery readings for testing and simulation.
    Scenarios:
      - 'healthy': steady normal discharge (5%/hr), regular charging cycles
      - 'degraded': accelerated discharge (15%/hr) in recent days, showing wear
      - 'gaps': multi-day gaps in tracking
      - 'clock_jumps': includes out-of-order timestamps
      - 'duplicate_rows': contains duplicate sensor reports
    """
    now = time.time()
    start_time = now - (days * 86400)
    current_time = start_time

    # Determine baseline vs degraded rates
    initial_discharge_rate = 5.0  # 5% per hour

    percent = 100
    charging = False

    while current_time < now:
        # Determine current discharge rate
        if scenario == "degraded" and current_time > (start_time + (days * 86400 * 0.5)):
            current_rate = 10.0  # Degraded: double discharge speed
        else:
            current_rate = initial_discharge_rate

        # Gap scenario: simulate 3-day absence
        if scenario == "gaps" and (start_time + 4 * 86400) <= current_time <= (start_time + 7 * 86400):
            current_time += 3 * 86400
            continue

        tracker.log_reading(device_id, "single", percent, 1 if charging else 0, current_time)

        if scenario == "duplicate_rows" and (int(current_time) % 5 == 0):
            # Attempt duplicate
            tracker.log_reading(device_id, "single", percent, 1 if charging else 0, current_time + 0.1)

        if scenario == "clock_jumps" and (int(current_time) % 7 == 0):
            # Clock anomaly
            tracker.log_reading(device_id, "single", max(0, percent - 5), 0, current_time - 300)

        # State transition: discharge or charge
        if not charging:
            # Drop over 30 minutes
            step_hours = 0.5
            drop = int(current_rate * step_hours)
            percent = max(10, percent - max(1, drop))
            current_time += 1800
            if percent <= 15:
                charging = True
        else:
            # Charge up in 1.5 hours
            percent = min(100, percent + 30)
            current_time += 1800
            if percent >= 100:
                charging = False
