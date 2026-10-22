# 🎧 TuneDeck — Terminal & Desktop Controller for JBL Devices (Linux, Windows, macOS)

> [!NOTE]
> **Trademark & Affiliation Disclaimer**: TuneDeck is an independent, community-driven open-source project and is not affiliated with, sponsored by, or endorsed by JBL, Harman International Industries, or Samsung Electronics. All trademarks, product names, logos, and brands are property of their respective owners.

A modern, high-performance cross-platform controller for JBL headphones, earbuds, and portable speakers. TuneDeck delivers both a rich terminal Textual TUI with a scriptable CLI, and a native Qt6 graphical desktop interface (`tunedeck-gui`) across **Linux**, **Windows**, and **macOS**.  
Control Active Noise Cancellation (ANC), Ambient Aware, TalkThru, multi-band graphical equalization, battery wear & retention tracking, and remote power management — right from your terminal or desktop.

---

## 📋 System Requirements & Platform Support

TuneDeck is built to run seamlessly across all major desktop operating systems:

| Platform | CLI & Terminal TUI (`tunedeck`) | Desktop GUI (`tunedeck-gui`) | Simulation Mode (`--sim`) | Physical Hardware Connection |
|---|:---:|:---:|:---:|---|
| **🐧 Linux** | ✅ Supported | ✅ Supported | ✅ Supported | BlueZ stack (`bluetoothctl`, RFCOMM ch 21) |
| **🪟 Windows** (10/11) | ✅ Supported | ✅ Supported | ✅ Supported | Windows Bluetooth stack (`AF_BLUETOOTH` / COM) |
| **🍏 macOS** (Intel & Apple Silicon) | ✅ Supported | ✅ Supported | ✅ Supported | Native UI & Simulation / CoreBluetooth |

### Platform-Specific Prerequisites

- **Python**: Version 3.10 or higher on all platforms.
- **Dependencies**:
  - *Core (CLI & TUI)*: `textual>=0.50.0`, `rich>=13.0.0`, `platformdirs>=4.0.0`
  - *Native Desktop GUI*: `PySide6-Essentials>=6.5.0` (installed via `pip install -e ".[gui]"`)

#### 🐧 Linux
- **Bluetooth Stack**: BlueZ with `bluetoothctl` installed and active (`systemctl status bluetooth`).
- **User Permissions**: Your user must have access to Bluetooth RFCOMM sockets (membership in `bluetooth` or `dialout` group):
  ```bash
  sudo usermod -aG bluetooth $USER
  # Log out and log back in for group changes to take effect
  ```

#### 🪟 Windows (10 & 11)
- **Terminal**: [Windows Terminal](https://aka.ms/terminal) (recommended for full UTF-8 and 24-bit truecolor rendering), PowerShell 7+, or standard Command Prompt.
- **Bluetooth**: Pair your JBL device through **Windows Settings > Bluetooth & devices**. Python 3.9+ on Windows supports native Bluetooth sockets (`socket.AF_BLUETOOTH`).
- **File Locking**: Automatic cross-platform file locking using `msvcrt` prevents concurrent instances from corrupting configuration or device state.

#### 🍏 macOS (macOS 12 Monterey through macOS 15 Sequoia)
- **Terminal**: Terminal.app, [iTerm2](https://iterm2.com/), or Ghostty.
- **Architecture**: Universal support for both Apple Silicon (M1/M2/M3/M4) and Intel x86_64 Macs.
- **Bluetooth Permissions**: When running hardware commands from Terminal, grant Bluetooth access if prompted, or verify in **System Settings > Privacy & Security > Bluetooth**.

---

## ✨ Features

- 🎧 **Comprehensive Multi-Model Catalog** — Support for 30 cataloged models across 4 device categories (Over-Ear, TWS Earbuds, Portable Speakers, PartyBox) and 11 model families (Tune, Live, Tour, Wave/Vibe, Endurance Peak, Flip, Charge, Xtreme, Boombox, Pulse, PartyBox) plus 3 fallback archetypes for uncataloged devices.
- 🖥️ **Native Desktop GUI (`tunedeck-gui`)** — Sleek dark desktop application built on Qt6/PySide6 with JBL Electric Orange (`#FF6600`) highlights, antialiased circular battery dials, real-time cubic spline EQ curves, device spotlight photography, and system tray integration (Windows notification area, macOS menu bar, Linux tray).
- 🔇 **Noise Control** — Switch between Active Noise Cancellation (ANC), Ambient Aware, TalkThru, and Off (gated per model capability).
- 🎚️ **Equalizer & Live Tuner** — Multi-band graphical EQ (10-band, 5-band, 3-band), standard presets (`flat`, `jazz`, `vocal`, `bass`, `club`), interactive `W, A, S, D` navigation in terminal, smooth sliders in GUI, and `Ctrl+S` / `Cmd+S` configuration persistence.
- 🔋 **Battery Health & Retention Estimator** — Tracks historical charge cycles in cross-platform SQLite storage. Derives estimated Equivalent Full Cycles (EFC), active discharge rate (%/hr), and retention degradation trends with confidence ratings (`low`, `medium`, `high`).
- ⚡ **Power Management** — Remote power-off command with safe hardware gating.
- 💻 **Rich Textual TUI** — Terminal interface featuring real-time EQ visualizers, TWS Trio gauges (Left, Right, Case), activity logs, and a toggleable Health panel.
- ⌨️ **Scriptable CLI** — Machine-readable `--json` output across status, health, and equalizer for desktop automation, Stream Decks, and keybinding daemons.
- 🧪 **Offline Simulator** — Full `--sim --model "<model>"` emulation for exploring and testing every feature on any platform without physical hardware.
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

Choose your platform below to set up your environment:

### 🐧 Linux & 🍏 macOS

```bash
# 1. Clone the repository and navigate to the project directory
git clone https://github.com/KVLNK12305/TuneDeck.git
cd TuneDeck

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install TuneDeck (use ".[gui]" to include the native Desktop GUI)
pip install -e ".[gui]"

# 4. List all supported JBL models
tunedeck cli models

# 5. Launch the Native Desktop GUI
tunedeck-gui

# 6. Or launch the Terminal TUI
tunedeck
```

### 🪟 Windows (PowerShell / Windows Terminal)

```powershell
# 1. Clone the repository and navigate to the project directory
git clone https://github.com/KVLNK12305/TuneDeck.git
cd TuneDeck

# 2. Create and activate a Python virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
# (Note: In standard Command Prompt 'cmd.exe', use: .venv\Scripts\activate.bat)

# 3. Install TuneDeck (use ".[gui]" to include the native Desktop GUI)
pip install -e ".[gui]"

# 4. List all supported JBL models
tunedeck cli models

# 5. Launch the Native Desktop GUI
tunedeck-gui

# 6. Or launch the Terminal TUI
tunedeck
```

---

## 🖥️ Native Desktop GUI (`tunedeck-gui`)

The native graphical interface delivers a first-class desktop experience with:
- **Device Spotlight**: High-definition product photos of your selected JBL hardware with capability badges (`ANC`, `Ambient`, `EQ`, `PartyBoost`, `Auracast`).
- **Dynamic Circular Battery Gauges**: Smooth antialiased gradient meters supporting both single-battery devices and TWS Trio mode (Left, Right, Case).
- **Interactive Graphic Equalizer**: Real-time cubic spline curve drawn through gain points with translucent orange fill, multi-band vertical sliders (-12 dB to +12 dB), and one-click presets.
- **System Tray Integration**: Minimizes to the system tray (Windows notification area, macOS menu bar, Linux system tray), shows live battery telemetry in tooltips, and offers quick noise mode switching.

```bash
# Launch GUI in simulation mode (works out of the box on all platforms without hardware)
tunedeck-gui --sim --model "JBL Tune 770NC"

# Launch GUI connected to physical Bluetooth hardware
tunedeck-gui --hardware --address "AA:BB:CC:DD:EE:FF"
```

---

## 🧪 Simulation Mode (No Hardware Required)

Explore any model's features, equalizer, battery gauges, and noise controls on **any OS** without needing physical hardware:

```bash
# Simulate a 10-band ANC headphone
tunedeck --sim --model "JBL Tune 770NC"

# Simulate TWS earbuds with trio battery (Left, Right, Case)
tunedeck --sim --model "JBL Tune 230NC TWS"

# Simulate a portable 3-band speaker
tunedeck --sim --model "JBL Flip 6"

# Simulate a PartyBox speaker with Auracast and lightshow
tunedeck --sim --model "JBL PartyBox Stage 320"
```

---

## ⚙️ Configuration

Configure your device's Bluetooth MAC address via environment variables or a configuration file:

### 1. Via Environment Variable

- **Linux & macOS (bash / zsh)**:
  ```bash
  export JBL_BD="AA:BB:CC:DD:EE:FF"
  # (or export TUNEDECK_BD="AA:BB:CC:DD:EE:FF")
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:JBL_BD="AA:BB:CC:DD:EE:FF"
  ```
- **Windows (Command Prompt)**:
  ```cmd
  set JBL_BD=AA:BB:CC:DD:EE:FF
  ```

### 2. Via Configuration File (`config.json`)

TuneDeck follows standard operating system directories using `platformdirs`:

| Operating System | Configuration Directory | Health Database Path |
|---|---|---|
| **🐧 Linux** | `~/.config/tunedeck/config.json` | `~/.local/share/tunedeck/health.db` |
| **🍏 macOS** | `~/Library/Application Support/tunedeck/config.json` *(or `~/.config/tunedeck/config.json`)* | `~/Library/Application Support/tunedeck/health.db` |
| **🪟 Windows** | `%APPDATA%\tunedeck\config.json` *(e.g. `C:\Users\<User>\AppData\Roaming\tunedeck\config.json`)* | `%LOCALAPPDATA%\tunedeck\health.db` |

#### Linux / macOS:
```bash
mkdir -p ~/.config/tunedeck
echo '{"bluetooth_address": "AA:BB:CC:DD:EE:FF"}' > ~/.config/tunedeck/config.json
```

#### Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path "$env:APPDATA\tunedeck"
'{"bluetooth_address": "AA:BB:CC:DD:EE:FF"}' | Out-File -Encoding utf8 "$env:APPDATA\tunedeck\config.json"
```

### 3. Discovering Paired Devices

- **Linux**: Discover paired JBL devices automatically:
  ```bash
  tunedeck cli scan
  ```
- **Windows**: Check paired devices under **Settings > Bluetooth & devices > Devices**, or via PowerShell:
  ```powershell
  Get-PnpDevice -Class Bluetooth | Where-Object { $_.FriendlyName -like "*JBL*" }
  ```
- **macOS**: View paired devices in **System Settings > Bluetooth**, or hold the `Option` key and click the **Apple Menu > System Information > Bluetooth**.

---

## ⚠️ Safety & Hardware Operation Notes

> [!CAUTION]
> - **Live Device Writes**: Commands (`anc`, `ambient`, `talkthru`, `noiseoff`, `eq`, and `poweroff`) transmit raw Airoha RACE protocol frames over Bluetooth RFCOMM channel 21 directly to the device firmware.
> - **Accidental Power-Off Protection**: Remote power-off on real hardware is protected by strict safety gating. In automated tests, it requires `--hardware`, a valid `JBL_BD` (or `TUNEDECK_BD`), and `JBLPC_ALLOW_POWEROFF=1` (or `TUNEDECK_ALLOW_POWEROFF=1`).
> - **Uncataloged Models**: If your device is not listed in `tunedeck cli models`, run `tunedeck cli diagnose` first to inspect detected capabilities before applying custom equalizer curves or power-off commands.

---

## 💻 CLI Commands

All commands can be invoked with `tunedeck cli <command>` (or using the alias `jblpc cli <command>`):

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
| `scan` | | Scan for paired JBL Bluetooth devices |
| `diagnose` | | Export diagnostic dump for uncataloged devices (`jbl_device_diagnostic.json`) |

---

## 🎚️ Equalizer Guide

View active EQ curve in the terminal:
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
Tune EQ interactively with live visual feedback:
```bash
tunedeck cli eq -i
# or: tunedeck cli eq --interactive
```
- **A / D** (or `←` / `→`): Navigate between frequency bands
- **W / S** (or `↑` / `↓`): Increase / decrease gain ($\pm 1\text{dB}$)
- **Ctrl+S** (or **Cmd+S** on macOS): Save active curve to `config.json` and apply to headset
- **Q**: Exit interactive tuner

### Preset Selection
```bash
tunedeck cli eq bass
tunedeck cli eq vocal
tunedeck cli eq jazz
tunedeck cli eq flat
tunedeck cli eq club
# Add --save to persist across launches:
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

## ⌨️ Keyboard Shortcuts

### Terminal TUI (`tunedeck`)

| Key | Action |
|---|---|
| `q` | Quit application |
| `c` | Connect to device via RFCOMM |
| `x` | Disconnect socket cleanly |
| `a` / `d` or `←` / `→` | Select active Equalizer frequency band |
| `w` / `s` or `↑` / `↓` | Increase / Decrease active band gain ($\pm 1\text{dB}$) |
| `Ctrl+S` / `Cmd+S` | Save active Equalizer preset & custom bands to `config.json` |
| `n` | Cycle Noise Modes (`Off` → `ANC` → `Ambient` → `TalkThru`) |
| `e` | Cycle Equalizer Presets (`Flat` → `Jazz` → `Vocal` → `Bass` → `Club`) |
| `h` | Toggle Battery Health & Retention panel |
| `b` | Refresh battery level |
| `p` | Power off headset (with confirmation dialog) |
| `m` | Toggle Simulation / Hardware mode |
| `1` | Direct Noise Off |
| `2` | Direct ANC |
| `3` | Direct Ambient Aware |
| `4` | Direct TalkThru |
| `r` | Full state refresh |

### Native Desktop GUI (`tunedeck-gui`)

- **Tab Navigation**: Switch between **Controls & Equalizer** and **Battery Health Analytics** tabs.
- **`Ctrl+S` / `Cmd+S`**: Save equalizer settings to `config.json`.
- **System Tray**: Click tray icon to restore or minimize to background; right-click for quick noise control and exit.

---

## 🧪 Testing & Verification

The comprehensive test suite runs 100% offline without requiring Bluetooth hardware:

### Linux & macOS
```bash
# Run the entire test suite and regenerate reports
./run_tests.sh
```

### Windows (PowerShell / CMD)
```powershell
# Run the pytest matrix
pytest -v
```

### Pytest Markers
- `-m "not hardware"`: Runs the full offline matrix across CLI subprocesses, headless Textual TUI pilot sessions, Qt6 offscreen GUI tests, fault injection scenarios, battery health tracking, and protocol verification (default).
- `-m "hardware"`: Runs against physical hardware when explicitly authorized (`--hardware`, `JBL_BD="XX:XX:XX:XX:XX:XX"`, and `JBLPC_ALLOW_POWEROFF=1`).

---

## 📚 Technical Documentation

- [Battery Hardware Register Probe Findings](docs/battery_probe.md)
- [Exception Coverage & Fault Injection Report](reports/exception_report.md)
- [Changelog of Bugs Fixed & Features Added](CHANGELOG.md)

---

## 📄 License

MIT
