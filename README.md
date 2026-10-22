# 🎧 TuneDeck

> [!NOTE]
> **Independent Open-Source Project**: TuneDeck is not affiliated with, sponsored by, or endorsed by JBL, Harman International Industries, or Samsung Electronics. All trademarks and brand names belong to their respective owners.

A cross-platform controller for JBL headphones, earbuds, and portable speakers across **Linux**, **Windows**, and **macOS**. Available as an interactive terminal dashboard (TUI), a native Qt6 desktop app (GUI), and a scriptable CLI.

---

## ✨ Features at a Glance

- 🔍 **Dynamic Device Detection** — Automatically recognizes your connected JBL device by its Harman Vendor ID and hardware broadcast. No hardcoded MAC addresses needed.
- 🎛️ **Model-Specific Controls** — Shows only the options your connected model actually supports. Unsupported buttons (e.g. Ambient Aware on non-ambient models, remote power-off on TWS earbuds) are automatically hidden.
- 🔇 **Noise Control** — Switch between Active Noise Cancellation (ANC), Ambient Aware, TalkThru, and Off (for supported headsets).
- 🎚️ **Equalizer** — Adaptive multi-band EQ (10-band, 5-band, or 3-band) with presets and interactive tuning.
- 🔋 **Battery Monitoring** — Real-time battery status, including Left, Right, and Case for TWS earbuds.
- 🖥️ **Three Interfaces** — Terminal dashboard (`tunedeck`), native desktop app (`tunedeck-gui`), and scriptable CLI (`tunedeck cli`).
- 🧪 **Offline Simulator** — Test any model's UI and features without hardware using `--sim`.

---

## 📋 Platform Support

| Platform | Terminal TUI (`tunedeck`) | Desktop GUI (`tunedeck-gui`) | CLI (`tunedeck cli`) | Simulation (`--sim`) | Bluetooth Backend |
|---|:---:|:---:|:---:|:---:|---|
| **🐧 Linux** | ✅ | ✅ | ✅ | ✅ | BlueZ (`bluetoothctl`, RFCOMM ch 21) |
| **🪟 Windows** (10/11) | ✅ | ✅ | ✅ | ✅ | Native Bluetooth (`AF_BLUETOOTH`) |
| **🍏 macOS** (Intel & Apple Silicon) | ✅ | ✅ | ✅ | ✅ | Native UI & CoreBluetooth |

### Prerequisites
- Python 3.10+
- Linux: BlueZ with `bluetoothctl` active and user in the `bluetooth` group.
- Windows: Paired via Windows Bluetooth settings.
- macOS: Terminal granted Bluetooth permissions when prompted.

---

## 🚀 Quick Start

### Linux & macOS

```bash
# 1. Clone repository
git clone https://github.com/KVLNK12305/TuneDeck.git
cd TuneDeck

# 2. Virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"

# 3. Launch
tunedeck          # Terminal TUI
tunedeck-gui      # Desktop GUI
tunedeck cli status  # CLI status
```

### Windows (PowerShell / Windows Terminal)

```powershell
# 1. Clone repository
git clone https://github.com/KVLNK12305/TuneDeck.git
cd TuneDeck

# 2. Virtual environment & dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[gui]"

# 3. Launch
tunedeck          # Terminal TUI
tunedeck-gui      # Desktop GUI
tunedeck cli status  # CLI status
```

---

## 🎧 Supported Models

TuneDeck includes profiles for 30 cataloged JBL devices across 4 categories:

- **Over-Ear / On-Ear**: Tune 770NC, 760NC, 720BT, 710BT, 670NC, 660NC, 520BT, 510BT; Live 770NC, 670NC, 660NC, 460NC; Tour ONE M2.
- **TWS Earbuds**: Live PRO 2 TWS, Tour PRO 2, Tune 230NC TWS, 130NC TWS, Tune Beam, Tune Flex, Wave/Vibe Buds, Endurance Peak 3.
- **Portable Speakers**: Flip 6, Charge 5, Xtreme 4, Boombox 3, Pulse 5.
- **PartyBox Speakers**: PartyBox 310, 110, Stage 320, Club 120.
- **Uncataloged Models**: Heuristic fallback profiles adapt controls automatically (`tunedeck cli diagnose` exports diagnostics).

Run `tunedeck cli models` to view the full catalog and capability flags.

---

## 🧪 Simulation Mode

Explore any device interface without physical hardware:

```bash
# Terminal TUI
tunedeck --sim --model "JBL Tune 770NC"
tunedeck --sim --model "JBL Flip 6"

# Desktop GUI
tunedeck-gui --sim --model "JBL Tune 230NC TWS"

# CLI
tunedeck cli --sim --model "JBL Live 660NC" status
```

---

## 💻 CLI Reference

Run `tunedeck cli <command>`:

| Command | Arguments | Description |
|---|---|---|
| `status` | `[--json]` | Display connection state, model, noise mode, and battery |
| `models` | | List all cataloged JBL models and capabilities |
| `health` | `[--json]` | Show battery health, estimated cycles, and discharge trends |
| `eq` | `[preset \| bands...] [--save] [--json]` | View or customize equalizer presets and band gain levels |
| `anc` | | Enable Active Noise Cancellation |
| `ambient` | | Enable Ambient Aware mode |
| `talkthru` | | Enable TalkThru mode |
| `noiseoff` | | Turn off noise processing |
| `battery` | | Display single battery gauge or TWS Left / Right / Case levels |
| `poweroff` | | Power off device remotely (headsets and speakers) |
| `scan` | | Scan for paired JBL Bluetooth devices |
| `diagnose` | | Export diagnostic dump for uncataloged devices |

### Quick Equalizer Examples

```bash
# Interactive terminal visualizer with W/A/S/D navigation
tunedeck cli eq -i

# Apply a preset (flat, jazz, vocal, bass, club)
tunedeck cli eq bass --save

# Set custom dB values (-12 to +12 dB)
tunedeck cli eq 5 4 3 2 1 0 -1 -2 -3 -4 --save
```

---

## ⌨️ Keyboard Shortcuts

### Terminal TUI (`tunedeck`)

| Key | Action |
|---|---|
| `q` | Quit |
| `c` / `x` | Connect / Disconnect |
| `n` | Cycle Noise Modes (`Off` → `ANC` → `Ambient` → `TalkThru`) |
| `e` | Cycle Equalizer Presets |
| `a` / `d` or `←` / `→` | Select EQ frequency band |
| `w` / `s` or `↑` / `↓` | Adjust band gain ($\pm 1\text{dB}$) |
| `Ctrl+S` / `Cmd+S` | Save EQ settings to `config.json` |
| `b` | Refresh battery level |
| `h` | Toggle Battery Health panel |
| `p` | Power off device (if supported) |
| `m` | Toggle Simulation / Hardware mode |
| `1`–`4` | Direct noise mode selection |

---

## ⚙️ Configuration

TuneDeck stores settings in your platform's standard configuration directory:
- **Linux**: `~/.config/tunedeck/config.json`
- **macOS**: `~/Library/Application Support/tunedeck/config.json`
- **Windows**: `%APPDATA%\tunedeck\config.json`

You can also specify a device via the `JBL_BD` environment variable:
```bash
export JBL_BD="AA:BB:CC:DD:EE:FF"
```

---

## 🧪 Testing

The offline test suite runs without requiring Bluetooth hardware:

```bash
pytest -q -m "not hardware"
```

---

## 📄 License

MIT
