# JBLPc Changelog

All notable changes, bug fixes, and additions developed for the end-to-end testing suite, multi-model catalog expansion, and battery health tracking system.

---

## [Unreleased] - 2026-10-20

### Added
- **Multi-Model Catalog Expansion (`jblpc/models.py`)**:
  - Expanded catalog from single model to 27 distinct JBL devices across 4 major families:
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
  - `tests/test_protocol.py`: Frame building, parsing, checksum verification, truncated frames, garbage byte recovery, oversized frames.
  - `tests/test_cli_e2e.py`: 326 subprocess test permutations executing every CLI command across all 27 cataloged models in isolated environments with strict timeouts.
  - `tests/test_tui_e2e.py`: Headless Textual TUI pilot tests exercising ANC, ambient, EQ band presets, and health toggle on TWS (`tune_230nc_tws`), headphone (`tune_770nc`), and speaker (`flip_6`).
  - `tests/test_fault_injection.py`: 20 deterministic fault injection tests covering adapter failure, missing tools, pairing issues, socket timeouts, corrupt configs, non-UTF8 strings, small terminals, and concurrency.
  - `tests/test_battery_health.py`: Synthetic discharge/charge history evaluation, database corruption handling, and confidence level assertions.
  - `tests/test_hardware.py`: Safety-gated real hardware integration tests requiring `--hardware`, `JBL_BD`, and `JBLPC_ALLOW_POWEROFF=1`.
- **System Hardening & Safety**:
  - `jblpc/lock.py`: Non-blocking POSIX `flock` single-instance locking to prevent socket collisions.
  - `jblpc/exceptions.py`: Comprehensive custom exception hierarchy preventing raw tracebacks.
  - `docs/battery_probe.md`: Detailed hardware battery register investigation across all JBL model families.
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
