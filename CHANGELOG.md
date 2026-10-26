# TuneDeck (JBLPc) Changelog

All notable changes, bug fixes, and additions developed for the end-to-end testing suite, multi-model catalog expansion, and battery health tracking system.

---

## [Unreleased] Accuracy pass - 2026-10-27

### Changed
- **Unverified hardware commands are opt-in**: EQ (`0x0A01`) and remote power-off (`0x0104`) use opcodes that no response from a real device has confirmed. They are now only sent when `TUNEDECK_EXPERIMENTAL=1` is set, and are logged as "sent, unconfirmed".
- **Speaker / PartyBox hardware control is refused** with a clear message. These devices use a different protocol from Airoha RACE, which is not implemented, so TuneDeck no longer sends RACE frames to them. Speaker and PartyBox profiles remain usable in `--sim`.
- **TWS battery on hardware** now shows the single level that is actually read, not "Unknown" Left/Right/Case values. Per-bud levels are not decoded.
- **Device detection**: Harman vendor IDs corrected to the Bluetooth SIG IDs `0x0057` / `0x075A`. `0x0ECB` is assigned to a different company (Zhong Shan City Richsound). Windows InstanceId matching now checks the `VID&` field, not any substring. Name matching now requires "JBL" in the name; generic words like "Live", "Charge" or "Club" matched non-JBL devices.
- macOS `check_device_paired` no longer reports any address as paired just because some JBL device exists.
- README platform table and feature list now match the implementation: macOS is simulation-only for control, and Windows hardware paths are untested.
- `docs/battery_probe.md` rewritten. It no longer presents unsourced per-family field tables as probe results.

### Fixed (GUI)
- **Dark theme on light desktops**: a later `QWidget { background: transparent }` rule overrode the `QMainWindow` background, so the system palette showed through (white on light themes). The rule order is fixed, and the app now uses Fusion with an explicit dark palette.
- **Cards never painted**: the `QFrame#cardFrame` style didn't match the `QWidget`-based cards. They now match `#cardFrame` and set `WA_StyledBackground`.
- **Squashed or overlapping layout**: the content needed more height than the window's minimum, so the EQ sliders, device name and gauge overlapped. Tabs now scroll when space is short (e.g. Steam Deck), and the default size is 1000×820.
- **Tab labels**: "Sound & Noise Control" rendered as "Sound _Noise Control" because `&` is a Qt mnemonic.
- **Noise control on models without ANC**: Wave/Vibe Buds and Endurance Peak 3 lost their Ambient and TalkThru buttons because the GUI gated on ANC only. The card is now hidden only when a model has no noise control at all.
- **Spotlight card**: the protocol tag and capability pills were clipped. Speaker and PartyBox profiles are now tagged "SIM ONLY".
- **Battery dial label** reads HEADPHONES / EARBUDS / SPEAKER instead of always "HEADSET".
- **Health metric cards**: a bare `QFrame` selector boxed every label inside them.
- The Save button shows the platform's shortcut (Cmd+S on macOS).
- **Possible crash on close**: background worker threads could emit into destroyed Qt objects (segfault in the GUI tests). The bridge now tracks its workers and waits for them on shutdown.

### Changed (GUI launch & connection)
- **`tunedeck-gui` connects to real hardware by default**, matching the TUI. Before, `--sim` defaulted to on and `--model` forced "JBL Tune 770NC", so the GUI never touched a device or detected its model. Use `--sim` for the simulator.
- **Unticking "Simulation Mode" can now connect.** Hardware mode used to start with an empty address, which skipped device discovery. Switching modes or models also always reported "Connected", even when the connection failed. It now reports the real result, and the checkbox starts in the actual mode.
- **Faster, accurate failure when Bluetooth is off**: a stopped BlueZ service is detected immediately (`systemctl is-active bluetooth`). Before, discovery waited about 8 s and then blamed a missing address. The full reason is shown in a banner under the header.
- The address of a successfully connected device is remembered for the next launch.
- New `scripts/install-launcher.sh` links `tunedeck` / `tunedeck-gui` into `~/.local/bin` (no venv activation needed) and adds a TuneDeck app-menu entry with a "simulation mode" action.
- The checkbox indicator is now visible on the dark theme.
- **No more Qt core dumps at launch on Linux/BSD**: a missing `libxcb-cursor` (Qt 6.5+ on X11) or a missing graphical session now prints what to do. Wayland sessions use Qt's Wayland backend automatically.
- **macOS fails fast**: without RFCOMM sockets, hardware connect stops immediately with a clear message, not after several slow `system_profiler` probes.
- README: added a per-system table of what to expect from the GUI.

### Removed
- RACE frame checksum support (`calculate_checksum`, `verify_checksum`, `with_checksum`, `verify_checksum_byte`). RACE frames have no checksum, and no real code path used it.
- Dead `OP_NOISE_SET_LEGACY` send fallback. It only ran after a socket send had already failed and disconnected, so it could never succeed.
- Unused `OP_EQ_GET` and `OP_DEVICE_INFO` constants.
- Hardcoded `"status": "PASS"` from `scripts/generate_exception_report.py`. The report now documents expected handling and points to `pytest -m fault` for verification.

### Corrections to earlier entries
- Earlier entries claimed TWS Left/Right/Case battery on hardware, BLE transport, checksum verification, macOS hardware support, and specific test counts ("451 tests", "326 permutations across 27 models"). None of these were accurate or verified. They are marked ~~struck~~ below.

---

## [Phase 2] Native Desktop GUI & Cross-Platform Engine - 2026-10-22

### Added
- **Native Cross-Platform Desktop GUI (`tunedeck_gui/`)**:
  - Independent native desktop application built with Qt6/PySide6, executable via `tunedeck-gui`.
  - Signature dark aesthetic in JBL Electric Orange (`#FF6600`) and onyx gray (`#121316`).
  - **Dynamic Battery Gauge (`BatteryGaugeWidget`)**:
    - Antialiased circular gauge with gradient ring indicator for headphones and speakers.
    - Automatic TWS Trio mode (Left, Right, Case) with independent telemetry rings and charging indicators.
  - **Segmented Noise Control (`NoiseControlWidget`)**:
    - Segmented pill selector for Active Noise Cancellation (ANC), Ambient Aware, TalkThru, and Off.
    - Hardware capability gating dynamically enabling/disabling controls based on active model profile.
  - **Graphic Equalizer Visualizer (`EqualizerWidget`)**:
    - Real-time cubic spline curve drawn through gain points with translucent orange gradient fill.
    - Multi-band vertical gain sliders (-12 dB to +12 dB) dynamically adapting to 10-band, 5-band, and 3-band hardware.
    - Quick preset buttons (`Flat`, `Bass Boost`, `Club`, `Vocal`, `Jazz`) and `Ctrl+S` persistence.
  - **Battery Health Panel (`HealthPanelWidget`)**:
    - Statistical telemetry cards for Equivalent Full Cycles (EFC), active discharge rate (%/hr), retention trends, and confidence ratings.
    - Interactive synthetic battery scenario generator (`healthy`, `degraded`, `gaps`, `clock_jumps`).
  - **Device Header Bar (`DeviceBarWidget`)**:
    - Real-time connection status dot, model selector dropdown across all 30 models, simulation toggle, and safe remote power-off confirmation dialog.
  - **Device Spotlight Card (`DeviceSpotlightWidget`)**:
    - High-fidelity product picture showcase for selected hardware with antialiased rounded corner masking.
    - Category badges, protocol tags (`AIROHA RACE`), and dynamic hardware capability tags (`ANC`, `Ambient`, `TalkThru`, `EQ`, `PartyBoost`, `Auracast`).
    - Smart hierarchical fallback for model families (`headphones.jpg`, `tws.jpg`, `speaker.jpg`, `partybox.jpg`) supporting exact per-model asset overrides.
  - **Refined Premium Typography & Emoji Removal**:
    - Complete removal of casual emojis across UI buttons, tabs, dials, status indicators, and headers in favor of clean high-contrast typography, colored status indicators, and sleek custom geometric vector icons.
  - **System Tray Integration (`QSystemTrayIcon`)**:
    - Minimizes to system tray, displays active battery percentages in tray menu and tooltips, quick noise mode switching.
- **Cross-Platform Hardening**:
  - `jblpc/lock.py`: Upgraded `SingleInstanceLock` to be cross-platform (supporting POSIX `fcntl` and Windows `msvcrt` without runtime crashes, with Windows temp/macOS cache fallbacks).
  - `jblpc/protocol.py`: Cross-platform Bluetooth device discovery and adapter telemetry (PowerShell on Windows, `system_profiler` on macOS, BlueZ `bluetoothctl` on Linux) with platform-aware `config.json` resolution (`%APPDATA%`, `Library/Application Support`, `~/.config`).
  - `jblpc/health.py`: Cross-platform SQLite `health.db` data directory resolution (`%LOCALAPPDATA%` on Windows, `Library/Application Support` on macOS).
  - `tunedeck_gui/windows/main_window.py`: Standard cross-platform shortcut bindings (`QKeySequence.StandardKey.Save` for `Ctrl+S` on Windows/Linux and `Cmd+S` on macOS).
  - `run_tests.ps1`: Native PowerShell test runner script for Windows environments.
  - `tunedeck_gui/bridge.py`: Re-entrant thread-safe controller bridge (`threading.RLock`) with queued Qt signal marshaling for smooth non-blocking UI.
- **Hardware Auto-Discovery & TUI Simulation Decoupling**:
  - `jblpc/__main__.py`, `jblpc/cli.py`, `tunedeck_gui/bridge.py`: Automatically discover paired JBL hardware on launch, match profile, and persist MAC address to `config.json` without requiring manual entry.
  - `jblpc/tui/app.py`: Removed silent automatic fallback into simulation mode; fixed banner to only display `[🧪 SIMULATOR]` badge when simulation mode is active.
  - Added dedicated `[🧪 Simulation]` / `[🔌 Hardware]` toggle button and `m` shortcut in TUI to explicitly switch modes.
  - Automatic hardware connection on TUI mount when a paired device address is available.
- **Hardware ANC & Telemetry Synchronization Fix**:
  - `jblpc/protocol.py`: Corrected Airoha RACE command opcode `OP_NOISE_SET = 0x0E06` ~~(with fallback to `0x0908`)~~, query payload `OP_NOISE_GET_PAYLOAD = 0500`, and added battery percentage parsing for `0x0403`.
  - Added `get_system_battery_level()` querying standard OS Bluetooth reporting (BlueZ `bluetoothctl` / UPower, macOS `system_profiler`, Windows PowerShell), preventing erroneous PMU status bytes from overriding actual battery percentage.
  - `jblpc/controller.py`: Drains initial unsolicited state notification frames upon RFCOMM socket connect, queries `0x0901` with proper `0500` payload, confirms set modes via response and notification parsing, and added non-blocking `poll()` for incoming unsolicited frames (e.g. physical headset button presses).
  - `jblpc/tui/app.py` & `tunedeck_gui/bridge.py`: Integrated non-blocking `poll()` into periodic refresh loops to update TUI and GUI displays in real-time when physical headset controls are pressed.
- **Headless Test Suite (`tests/test_gui.py`, `tests/test_tui_e2e.py`, `tests/test_protocol.py`)**:
  - ~~451 automated unit and integration tests passing (100%)~~ Automated unit and integration tests, with dedicated tests for unsolicited notification frames and battery percentage parsing.

---

## [Unreleased] - 2026-10-20
- **Multi-Model Catalog Expansion (`jblpc/models.py`)**:
  - Expanded catalog to 30 distinct JBL devices across 4 major families:
    - *Over-Ear & On-Ear*: Tune 770NC, 760NC, 720BT, 710BT, 670NC, 660NC, 520BT, 510BT, Live 770NC, 670NC, 660NC, 460NC, Tour ONE M2.
    - *True Wireless (TWS)*: Tune 230NC TWS, 130NC TWS, Tune Beam, Tune Flex, Live PRO 2 TWS, Tour PRO 2, Wave/Vibe Buds, Endurance Peak 3.
    - *Portable Speakers*: Flip 6, Charge 5, Xtreme 4, Boombox 3, Pulse 5.
    - *PartyBox Series*: PartyBox Stage 320, PartyBox Club 120, PartyBox 310, PartyBox 110.
  - Added feature flags per profile: `has_anc`, `has_ambient_aware`, `has_talkthru`, `has_spatial_audio`, `has_smart_talk`, `has_partyboost`, `has_auracast`, `has_lightshow`, and `has_power_off_command`.
  - Added 3 fallback profile archetypes (`fallback_headphones`, `fallback_tws`, `fallback_speaker`) to support uncataloged models automatically.
- **Battery Health Tracking & Estimation (`jblpc/health.py`)**:
  - `BatteryHealthTracker`: Thread-safe SQLite persistence under `~/.local/share/jblpc/health.db`.
  - Automatic Equivalent Full Cycle (EFC) estimation: mathematically derived as `sum(Δupward charge movements) / 100`.
  - Active discharge rate calculation (%/hour) computed during playback intervals.
  - Retention trend analysis comparing current discharge rate against baseline observation window.
  - Explicit three-tier confidence metrics (`low`, `medium`, `high`) based on data duration and sample volume.
  - Plain-language disclaimers and notes on all estimated metrics.
  - `jblpc cli health` command with Rich table and `--json` machine-readable output.
  - `jblpc cli battery-log` background polling tool with `--interval` and `--count` flags.
  - Interactive TUI `HealthWidget` toggled via keyboard shortcut `h`.
  - Synthetic battery scenario generation (`healthy`, `degraded`, `gaps`, `clock_jumps`, `duplicate_rows`).
- **Equalizer Tuning & Keyboard Control (`jblpc/cli.py`, `jblpc/controller.py`, `jblpc/tui/app.py`)**:
  - `W, A, S, D` Keyboard Navigation:
    - `A` / `D` (or $\leftarrow$ / $\rightarrow$): Navigate between frequency bands with dynamic visual selection indicators (`▼`, inverted badge, highlighted levels).
    - `W` / `S` (or $\uparrow$ / $\downarrow$): Increase / decrease active band gain by $\pm 1\text{dB}$ (within $-12\text{dB}$ to $+12\text{dB}$).
  - `Ctrl+S` Terminal Configuration Persistence: Saves active EQ preset and custom band gains to `~/.config/jblpc/config.json` and automatically restores them upon reconnecting.
  - Interactive Terminal Tuner (`jblpc cli eq -i` / `--interactive`): Dedicated in-terminal tuner with live ASCII visualizer and real-time WASD / Ctrl+S controls.
  - `jblpc cli eq save` and `--save` flag for CLI preset and custom band persistence.
  - `jblpc cli eq`: View active EQ curve and band gain levels with rich terminal ASCII visualizer.
  - Preset switching: `jblpc cli eq flat`, `jazz`, `vocal`, `bass`, `club`.
  - Custom band gains: `jblpc cli eq 5 4 3 2 1 0 -1 -2 -3 -4` or `jblpc cli eq --bands=...`.
  - Machine-readable `--json` format for automated audio scripting.
  - TUI shortcut `e` to cycle standard EQ presets in real-time.
  - Capability checks preventing EQ commands on non-EQ hardware (e.g. Tune 510BT) with clean exit codes.
- **Comprehensive End-to-End Test Suite (`tests/`)**:
  - `tests/test_protocol.py`: Frame building, parsing, ~~checksum verification,~~ truncated frames, garbage byte recovery, oversized frames.
  - `tests/test_cli_e2e.py`: Subprocess tests executing CLI commands across ~~all 27~~ the cataloged models in isolated environments with strict timeouts.
  - `tests/test_tui_e2e.py`: Headless Textual TUI pilot tests exercising ANC, ambient, EQ band presets, and health toggle on TWS (`tune_230nc_tws`), headphone (`tune_770nc`), and speaker (`flip_6`).
  - `tests/test_fault_injection.py`: 20 deterministic fault injection tests covering adapter failure, missing tools, pairing issues, socket timeouts, corrupt configs, non-UTF8 strings, small terminals, and concurrency.
  - `tests/test_battery_health.py`: Synthetic discharge/charge history evaluation, database corruption handling, and confidence level assertions.
  - `tests/test_hardware.py`: Safety-gated real hardware integration tests requiring `--hardware`, `JBL_BD`, and `JBLPC_ALLOW_POWEROFF=1`.
- **System Hardening & Safety**:
  - `jblpc/lock.py`: Non-blocking POSIX `flock` single-instance locking to prevent socket collisions.
  - `jblpc/exceptions.py`: Comprehensive custom exception hierarchy preventing raw tracebacks.
  - `docs/battery_probe.md`: ~~Detailed hardware battery register investigation across all JBL model families.~~ Notes on which battery data is read (rewritten 2026-10-27).
  - `scripts/generate_exception_report.py`: Automated AST codebase scanner and exception report generator.
  - `run_tests.sh`: One-command automated test runner with virtualenv setup, pytest execution, and report generation.

### Fixed
1. **Noise Mode Capability Checks in `HeadsetController`**:
   - *Issue*: `set_noise_mode` checked `p.has_anc` for all modes except `OFF`. Models like Wave Buds and Endurance Peak 3 that support Ambient Aware / TalkThru without ANC were falsely rejected.
   - *Fix*: Gated each mode against its specific capability (`p.has_ambient_aware`, `p.has_talkthru`, `p.has_anc`), and updated `cycle_noise_mode` to cycle between whichever subset of modes the hardware supports.
2. **Rich Console Wrapping in JSON Machine Output**:
   - *Issue*: `jblpc cli health --json` used `console.print(json.dumps(...))`, which injected soft-wrap newlines into strings on narrow terminal displays, corrupting JSON parsing.
   - *Fix*: Changed to direct `print(json.dumps(out, indent=2))` for all machine-readable output.
3. **Controller Init Model Parameter Ambiguity**:
   - *Issue*: `HeadsetController` expected `model` parameter, raising `TypeError` when called with `model_id`.
   - *Fix*: Accepted both `model` and `model_id` keyword arguments.
4. **Corrupt SQLite Database Auto-Recovery**:
   - *Issue*: Corrupted or malformed SQLite database files caused unhandled `sqlite3.DatabaseError` upon launch.
   - *Fix*: Added automatic recovery in `BatteryHealthTracker._init_db()` that moves corrupt files to a `.corrupt.<timestamp>` backup and initializes a clean schema.
5. **Swallowed Exceptions in TUI DOM Queries**:
   - *Issue*: 13 DOM queries in `jblpc/tui/app.py` used `except Exception: pass`, which masked unrelated runtime errors.
   - *Fix*: Narrowed handlers specifically to `except NoMatches:` from `textual.css.query`.
6. **Missing RFCOMM Channel in Default Configuration**:
   - *Issue*: `load_config` did not supply `rfcomm_channel: 21` when `config.json` was missing.
   - *Fix*: Added default `rfcomm_channel: 21` to fallback dictionary.
7. **Single Instance Lock Argument Alias**:
   - *Issue*: `SingleInstanceLock` accepted `name` but test and CLI invocations referenced `lock_name`.
   - *Fix*: Added `lock_name` alias to `SingleInstanceLock.__init__`.
