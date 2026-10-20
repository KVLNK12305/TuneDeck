# 🎧 TuneDeck — Terminal Controller for JBL Devices on Linux

> [!NOTE]
> **Trademark & Affiliation Disclaimer**: TuneDeck is an independent, community-driven open-source project and is not affiliated with, sponsored by, or endorsed by JBL, Harman International Industries, or Samsung Electronics. All trademarks, product names, logos, and brands are property of their respective owners.

A modern, high-performance terminal controller and Textual TUI for JBL headphones, earbuds, and portable speakers on Linux.  
Control Active Noise Cancellation (ANC), Ambient Aware, TalkThru, multi-band graphical equalization, battery wear & retention tracking, and remote power management — right from your terminal.

---

## 📋 System Requirements

- **Operating System**: Linux (Ubuntu, Debian, Fedora, Arch Linux, openSUSE, etc.)
- **Python**: Version 3.10 or higher
- **Bluetooth Stack**: BlueZ with `bluetoothctl` installed and active (`systemctl status bluetooth`)
- **Permissions**: Your user must have access to Bluetooth RFCOMM sockets (typically accomplished by membership in the `bluetooth` or `dialout` group):
  ```bash
  sudo usermod -aG bluetooth $USER
  # Log out and log back in for group changes to take effect
  ```
- **Dependencies**: `textual>=0.50.0`, `rich>=13.0.0`, `platformdirs>=4.0.0`

---

## ✨ Features

- 🎧 **Comprehensive Multi-Model Catalog** — Support for 30 cataloged models across 4 device categories (Over-Ear, TWS Earbuds, Portable Speakers, PartyBox) and 11 model families (Tune, Live, Tour, Wave/Vibe, Endurance Peak, Flip, Charge, Xtreme, Boombox, Pulse, PartyBox) plus 3 fallback archetypes for uncataloged devices.
- 🔇 **Noise Control** — Switch between Active Noise Cancellation (ANC), Ambient Aware, TalkThru, and Off (gated per model capability).
- 🎚️ **Equalizer & Live Tuner** — In-terminal ASCII curve visualizer, standard presets (`flat`, `jazz`, `vocal`, `bass`, `club`), custom band gain tuning (10-band, 5-band, 3-band), interactive `W, A, S, D` navigation, and `Ctrl+S` configuration persistence.
- 🔋 **Battery Health & Retention Estimator** — Tracks historical charge cycles in local SQLite (`~/.local/share/tunedeck/health.db` or `~/.local/share/jblpc/health.db`). Derives estimated Equivalent Full Cycles (EFC), active discharge rate (%/hr), and retention degradation trends with confidence ratings (`low`, `medium`, `high`).
- ⚡ **Power Management** — Remote power-off command with safe hardware gating.
- 🖥️ **Rich Textual TUI** — Dark aesthetic in signature orange (`#FF6600`), featuring real-time EQ sliders, TWS Trio gauges (Left, Right, Case), activity logs, and a toggleable Health panel.
- ⌨️ **Scriptable CLI** — Machine-readable `--json` output across status, health, and equalizer for desktop automation and keybinding daemons.
- 🧪 **Offline Simulator** — Full `--sim --model "<model>"` emulation for testing every feature without requiring physical hardware.
- 🔬 **Built-in Diagnostics** — Automated RFCOMM channel probe and diagnostic dump export (`tunedeck cli diagnose`) to submit support for new hardware.

---

## 🔍 Hardware Verification Status

| Category | Model / Family | Verification Tier | Capabilities Supported |
|---|---|---|---|
| **Over-Ear** | JBL Tune 770NC | **Verified on Hardware** | ANC, Ambient Aware, TalkThru, Off, Battery Telemetry, 10-Band EQ, Remote Power-Off |
| **Over-Ear** | Live 770NC, 670NC, 660NC, 460NC, Tour ONE M2 | **Simulator & Protocol Validated** | ANC, Ambient Aware, TalkThru, Spatial Audio (Live/Tour), 10-Band EQ, Battery, Remote Power-Off |
| **Over-Ear** | Tune 760NC, 670NC, 660NC | **Simulator & Protocol Validated** | ANC, Off, 10-Band EQ, Battery, Remote Power-Off (Ambient/TalkThru on 670NC; 760NC/660NC ANC-only) |
| **Over-Ear** | Tune 720BT, 710BT, 520BT | **Simulator & Protocol Validated** | Battery Telemetry, 10-Band EQ, Remote Power-Off |
| **Over-Ear** | Tune 510BT | **Simulator & Protocol Validated** | Battery Telemetry, Remote Power-Off (Non-EQ Hardware) |
| **TWS Earbuds** | Live PRO 2 TWS, Tour PRO 2 | **Simulator & Protocol Validated** | ANC, Ambient Aware, TalkThru, Spatial Audio, Trio Battery (Left/Right/Case), 10-Band EQ |
| **TWS Earbuds** | Tune 230NC TWS, 130NC TWS, Tune Beam, Tune Flex | **Simulator & Protocol Validated** | ANC, Ambient Aware, TalkThru, Trio Battery (Left/Right/Case), 5-Band EQ |
| **TWS Earbuds** | Wave / Vibe Buds, Endurance Peak 3 | **Simulator & Protocol Validated** | Ambient Aware, TalkThru, Trio Battery (Left/Right/Case), 5-Band EQ (ANC non-supported) |
| **Speakers** | Flip 6, Charge 5, Xtreme 4, Boombox 3, Pulse 5 | **Simulator & Protocol Validated** | Battery Telemetry, 3-Band EQ, PartyBoost / Auracast Flags, Lightshow (Pulse 5), Remote Power-Off |
| **PartyBox** | PartyBox 310, 110, Stage 320, Club 120 | **Simulator & Protocol Validated** | Battery / AC Power Telemetry, 3-Band EQ, Auracast (Stage/Club), Lightshow Controls, Remote Power-Off |
| **Uncataloged** | Other JBL Bluetooth Devices | **Generic Fallback & Diagnostics** | Heuristic fallback profiles (Headphones, TWS, Speaker) + `tunedeck cli diagnose` export |

---

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install TuneDeck in editable mode
pip install -e .

# 3. List all supported JBL models
tunedeck cli models
# (Note: 'jblpc' remains available as an alias)

# 4. Launch the TUI
tunedeck
```

### Simulation Mode (No Hardware Required)
Explore any model's UI and capabilities without needing physical hardware:
```bash
# Simulate a 10-band ANC headphone
tunedeck --sim --model "JBL Tune 770NC"

# Simulate TWS earbuds with trio battery (Left, Right, Case)
tunedeck --sim --model "JBL Tune 230NC TWS"

# Simulate a portable 3-band speaker
tunedeck --sim --model "JBL Flip 6"
```

---

## ⚙️ Configuration

Set your device's Bluetooth MAC address:

```bash
# Via environment variable
export JBL_BD="AA:BB:CC:DD:EE:FF"
# (or export TUNEDECK_BD="AA:BB:CC:DD:EE:FF")

# Or via XDG config file (~/.config/tunedeck/config.json or ~/.config/jblpc/config.json)
mkdir -p ~/.config/tunedeck
echo '{"bluetooth_address": "AA:BB:CC:DD:EE:FF"}' > ~/.config/tunedeck/config.json
```

Discover paired JBL devices on your system:
```bash
tunedeck cli scan
```

---

## ⚠️ Safety & Hardware Operation Notes

> [!CAUTION]
> - **Live Device Writes**: Commands (`anc`, `ambient`, `talkthru`, `noiseoff`, `eq`, and `poweroff`) transmit raw Airoha RACE protocol frames over Bluetooth RFCOMM channel 21 directly to the device firmware.
> - **Accidental Power-Off Protection**: Remote power-off on real hardware is protected by strict safety gating. In automated tests, it requires `--hardware`, a valid `JBL_BD` (or `TUNEDECK_BD`), and `JBLPC_ALLOW_POWEROFF=1` (or `TUNEDECK_ALLOW_POWEROFF=1`).
> - **Uncataloged Models**: If your device is not listed in `tunedeck cli models`, run `tunedeck cli diagnose` first to inspect detected capabilities before applying custom equalizer curves or power-off commands.

---

## 💻 CLI Commands

| Command | Arguments | Description |
|---|---|---|
| `status` | `[--json]` | Display connection state, model, noise mode, EQ preset, and battery levels |
| `models` | | List all cataloged JBL models, categories, and hardware capability flags |
| `health` | `[--json]` | Show estimated battery health, equivalent full cycles (EFC), discharge rate & retention |
| `battery-log`| `[--interval N] [--count N]` | Background polling daemon recording battery readings into SQLite |
| `eq` | `[preset \| bands...] [--save] [--json]` | View graphical EQ curve, activate a preset, or apply custom band dB gains |
| `anc` | | Enable Active Noise Cancellation |
| `ambient` | | Enable Ambient Aware mode |
| `talkthru` | | Enable TalkThru mode |
| `noiseoff` | | Turn off noise control / ambient modes |
| `battery` | | Display single battery gauge or TWS Left / Right / Case levels |
| `poweroff` | | Power off device remotely (headsets and speakers) |
| `scan` | | Scan for paired JBL Bluetooth devices via `bluetoothctl` |
| `diagnose` | | Export diagnostic dump for uncataloged devices (`jbl_device_diagnostic.json`) |

---

## 🎚️ Equalizer Guide

View active EQ curve:
```bash
tunedeck cli eq
```
```text
🎚️ Equalizer — JBL Tune 770NC (10_BAND)
  Active Preset: Bass Boost

+12dB │  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·  
 +9dB │  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·  
 +6dB │  █    ·    ·    ·    ·    ·    ·    ·    ·    ·  
 +3dB │  █    █    █    ·    ·    ·    ·    ·    ·    ·  
 +0dB │  ─    ─    ─    ─    █    █    █    █    █    █  
 -3dB │  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·  
 -6dB │  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·  
 -9dB │  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·  
-12dB │  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·  
       └──────────────────────────────────────────────────
        32Hz  64Hz 125Hz 250Hz 500Hz  1kHz  2kHz  4kHz  8kHz 16kHz
        +6dB  +5dB  +4dB  +2dB  +0dB  +0dB  +0dB  +0dB  +0dB  +0dB 
```

### Interactive Equalizer Tuning
Tune EQ interactively in the terminal with live visual feedback:
```bash
tunedeck cli eq -i
# or: tunedeck cli eq --interactive
```
- **A / D** (or `←` / `→`): Navigate between frequency bands
- **W / S** (or `↑` / `↓`): Increase / decrease gain ($\pm 1\text{dB}$)
- **Ctrl+S**: Save active curve to config (`~/.config/tunedeck/config.json`) and apply to headset
- **Q**: Exit interactive tuner

### Preset Selection
```bash
tunedeck cli eq bass
tunedeck cli eq vocal
tunedeck cli eq jazz
tunedeck cli eq flat
tunedeck cli eq club
# Add --save to remember this preset across launches:
tunedeck cli eq bass --save
```

### Custom Band Gains
Set custom band dB values ($-12\text{dB}$ to $+12\text{dB}$):
```bash
# 10-band models (e.g. Tune 770NC):
tunedeck cli eq 5 4 3 2 1 0 -1 -2 -3 -4 --save

# Or via --bands flag:
tunedeck cli eq --bands=6,5,4,2,0,0,0,0,0,0 --save
```

Save current EQ to configuration:
```bash
tunedeck cli eq save
```

---

## 🔋 Battery Health & Wear Estimator

> [!IMPORTANT]
> **Measurement Notice**: JBL Bluetooth firmware exposes state-of-charge percentage (0–100%) and charging flags, but does **not** expose hardware cycle counters, cell wear registers, or design capacity over Bluetooth. **All cycle counts, discharge rates, and retention percentages calculated by TuneDeck (JBLPc) are mathematical estimates derived from usage telemetry, NOT hardware wear registers.**

- **Equivalent Full Cycles (EFC)**: Derived as $\sum \Delta \text{charge}_{\text{positive}} / 100$, tracking only upward charging movements (discharging is excluded).
- **Discharge Rate**: Linear regression of battery loss during active playback (%/hour).
- **Retention Trend**: Comparison of active discharge rate against the initial baseline observation period.
- **Confidence Tiers**: Automatically classified as `low` (<24h data or <10 samples), `medium` (1–7 days), or `high` (≥7 days, ≥30 samples).

```bash
# View battery health overview table
tunedeck cli health

# Export machine-readable JSON health report
tunedeck cli health --json

# Run background polling logger
tunedeck cli battery-log --interval 300 --count 12
```

---

## ⌨️ TUI Keyboard Shortcuts

| Key | Action |
|---|---|
| `q` | Quit application |
| `c` | Connect to device via RFCOMM channel 21 |
| `x` | Disconnect socket cleanly |
| `a` / `d` or `←` / `→` | Select active Equalizer frequency band |
| `w` / `s` or `↑` / `↓` | Increase / Decrease active band gain ($\pm 1\text{dB}$) |
| `Ctrl+S` | Save active Equalizer preset & custom bands to `config.json` |
| `n` | Cycle Noise Modes (`Off` → `ANC` → `Ambient` → `TalkThru`) |
| `e` | Cycle Equalizer Presets (`Flat` → `Jazz` → `Vocal` → `Bass` → `Club`) |
| `h` | Toggle Battery Health & Retention panel |
| `b` | Refresh battery level |
| `p` | Power off headset |
| `1` | Direct Noise Off |
| `2` | Direct ANC |
| `3` | Direct Ambient Aware |
| `4` | Direct TalkThru |
| `r` | Full state refresh |

---

## 🧪 Testing & Verification

The test suite runs 100% offline without requiring Bluetooth hardware:

```bash
# Run the entire test suite and regenerate reports
./run_tests.sh
```

### Pytest Markers
- `-m "not hardware"`: Runs the full offline matrix across CLI subprocesses, headless Textual TUI pilot sessions, fault injection scenarios, battery health tracking, and protocol verification (default).
- `-m "hardware"`: Runs against physical hardware when explicitly authorized (`--hardware`, `JBL_BD="XX:XX:XX:XX:XX:XX"`, and `JBLPC_ALLOW_POWEROFF=1`).

---

## 📚 Technical Documentation

- [Battery Hardware Register Probe Findings](docs/battery_probe.md)
- [Exception Coverage & Fault Injection Report](reports/exception_report.md)
- [Changelog of Bugs Fixed & Features Added](CHANGELOG.md)

---

## 📄 License

MIT
