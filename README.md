<p align="center">
  <img src="assets/logo.png" alt="TuneDeck Logo" width="220">
</p>

<h1 align="center">TuneDeck</h1>

<p align="center">
  <em>headphones, from your shell</em>
</p>

<p align="center">
  <a href="#-features-at-a-glance">Features</a> •
  <a href="#-platform-support">Platform Support</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-supported-models">Supported Models</a> •
  <a href="#-cli-reference">CLI Reference</a>
</p>

---

> [!NOTE]
> **Independent Open-Source Project**: TuneDeck is not affiliated with, sponsored by, or endorsed by JBL, Harman International Industries, or Samsung Electronics. All trademarks and brand names belong to their respective owners.

A cross-platform controller for JBL headphones, earbuds, and portable speakers across **Linux**, **Windows**, and **macOS**. Available as an interactive terminal dashboard (TUI), a native Qt6 desktop app (GUI), and a scriptable CLI.

---

## ✨ Features at a Glance

- 🔍 **Dynamic Device Detection** — Finds your paired JBL device by its name, or by Harman's Bluetooth vendor ID if you renamed it (Linux). No hardcoded MAC addresses needed.
- 🎛️ **Model-Specific Controls** — Shows only the options your connected model actually supports. Unsupported buttons (e.g. Ambient Aware on non-ambient models, remote power-off on TWS earbuds) are automatically hidden.
- 🔇 **Noise Control** — Switch between Active Noise Cancellation (ANC), Ambient Aware, TalkThru, and Off (for supported headsets).
- 🎚️ **Equalizer** — Multi-band EQ (10-band, 5-band, or 3-band) with presets and interactive tuning. *Sending EQ to real hardware is experimental* (see [Hardware Status](#-hardware-status)).
- 🔋 **Battery Monitoring** — Battery level from your OS Bluetooth stack. Left / Right / Case levels for TWS earbuds are shown in the simulator only.
- 🖥️ **Three Interfaces** — Terminal dashboard (`tunedeck`), native desktop app (`tunedeck-gui`), and scriptable CLI (`tunedeck cli`).
- 🧪 **Offline Simulator** — Test any model's UI and features without hardware using `--sim`.

---

## 📋 Platform Support

| Platform | TUI / GUI / CLI | Simulation (`--sim`) | Device Discovery | Hardware Control | Bluetooth Backend |
|---|:---:|:---:|:---:|:---:|---|
| **🐧 Linux** | ✅ | ✅ | ✅ | ✅ | BlueZ (`bluetoothctl`) + RFCOMM ch 21 socket |
| **🪟 Windows** (10/11) | ✅ | ✅ | ⚠️ untested | ⚠️ untested | PowerShell PnP queries + Python `AF_BLUETOOTH` RFCOMM socket |
| **🍏 macOS** | ✅ | ✅ | ⚠️ untested | ❌ | `system_profiler` for discovery only; Python has no RFCOMM sockets on macOS |

### Prerequisites
- Python 3.10+
- Linux: BlueZ with `bluetoothctl` active and user in the `bluetooth` group.
- Linux GUI on X11: the `libxcb-cursor` library (Qt 6.5+ needs it). On Ubuntu/Debian, run `sudo apt install libxcb-cursor0`.
- Windows: Paired via Windows Bluetooth settings.
- macOS: Simulation only. Discovery may list your device, but TuneDeck cannot connect to it.

### What to Expect from the GUI on Each System

The desktop window opens wherever PySide6 runs. Hardware control has fewer options: TuneDeck has been tested on real hardware only on Linux. If the GUI can't connect, it explains why in a red banner under the header, and **Simulation Mode** is always available.

| System | What happens |
|---|---|
| **Linux desktop** (Ubuntu, Fedora, KDE, GNOME…) | Opens and connects to your paired headphones when the Bluetooth service is running. |
| **Linux, X11 without `libxcb-cursor`** (e.g. a fresh Ubuntu 22.04) | Prints the install command for your distro instead of crashing. |
| **Linux, Wayland session** | Uses Qt's Wayland backend automatically, so `libxcb-cursor` is not needed. |
| **Linux, Bluetooth service stopped** (common in VMs) | Opens; the banner says to run `sudo systemctl enable --now bluetooth`. In a VM, pass the host's Bluetooth adapter through to the guest first. |
| **No graphical session** (SSH, server, TTY) | Says so and suggests the terminal UI (`tunedeck`). |
| **SteamOS** (Desktop Mode) | Expected to behave like Linux desktop. Untested. |
| **Windows 10/11** | Opens. Hardware control uses PowerShell and Python's Bluetooth sockets. Untested on real devices. A console window stays open behind the GUI. |
| **macOS** (Intel & Apple Silicon) | Opens; simulation mode works fully. Hardware control is not possible because Python has no Bluetooth RFCOMM sockets on macOS, and the banner says so immediately. |
| **WSL2 / Chromebook Linux** | Opens, but there is no Bluetooth, so use simulation mode. |
| **Raspberry Pi** | 64-bit OS should work like Linux desktop. 32-bit has no PySide6 package, so use the terminal UI. |
| **FreeBSD / OpenBSD** | No PySide6 on pip; hardware control is not supported. Use simulation mode if you install PySide6 from your ports system. |
| **Python older than 3.10** | `pip install` refuses; upgrade Python first. |

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
tunedeck-gui      # Desktop GUI (connects to your paired JBL device; add --sim for the simulator)
tunedeck cli status  # CLI status

# 4. Optional (Linux / SteamOS Desktop Mode): run without activating the venv,
#    and add TuneDeck to your app menu
scripts/install-launcher.sh   # undo with: scripts/install-launcher.sh --uninstall
```

> **Not connecting?** The GUI shows the reason in a banner under the header. The most common one on Linux is that the Bluetooth service is stopped (`sudo systemctl enable --now bluetooth`), or that the headphones are not paired in your system Bluetooth settings yet.

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
tunedeck-gui      # Desktop GUI (connects to your paired JBL device; add --sim for the simulator)
tunedeck cli status  # CLI status
```

---

## 🎧 Supported Models

TuneDeck includes capability profiles for 30 cataloged JBL devices. Profiles decide which controls the UI shows. They come from public product specs and have not been tested on each model.

- **Over-Ear / On-Ear** *(hardware control: Airoha RACE)*: Tune 770NC, 760NC, 720BT, 710BT, 670NC, 660NC, 520BT, 510BT; Live 770NC, 670NC, 660NC, 460NC; Tour ONE M2.
- **TWS Earbuds** *(hardware control: Airoha RACE)*: Live PRO 2 TWS, Tour PRO 2, Tune 230NC TWS, 130NC TWS, Tune Beam, Tune Flex, Wave/Vibe Buds, Endurance Peak 3.
- **Portable Speakers** *(simulator only)*: Flip 6, Charge 5, Xtreme 4, Boombox 3, Pulse 5.
- **PartyBox Speakers** *(simulator only)*: PartyBox 310, 110, Stage 320, Club 120.
- **Uncataloged Models**: Fallback profiles pick controls from the device name (`tunedeck cli diagnose` exports diagnostics).

---

## 🔬 Hardware Status

What actually goes over the wire, and how sure we are about it:

| Feature | Status on real hardware |
|---|---|
| Noise control (ANC / Ambient / TalkThru / Off) | ✅ Confirmed on a physical Airoha RACE headset; mode changes from the headset's own button are picked up |
| Battery level | ✅ Read from the OS Bluetooth stack (BlueZ / UPower, Windows PnP); RACE battery query is an unverified fallback |
| TWS Left / Right / Case battery | ❌ Not decoded; a single level is shown |
| Equalizer | ⚠️ Experimental: opcode and payload unverified, no acknowledgement read. Requires `TUNEDECK_EXPERIMENTAL=1` |
| Remote power-off | ⚠️ Experimental: opcode unverified. Requires `TUNEDECK_EXPERIMENTAL=1` |
| Firmware version | ❌ Not read |
| Speakers / PartyBox | ❌ They use a different protocol, which is not implemented |

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
| `eq` | `[preset \| bands...] [--save] [--json]` | View or customize equalizer presets and band gain levels (hardware: experimental) |
| `anc` | | Enable Active Noise Cancellation |
| `ambient` | | Enable Ambient Aware mode |
| `talkthru` | | Enable TalkThru mode |
| `noiseoff` | | Turn off noise processing |
| `battery` | | Display battery level (TWS Left / Right / Case in simulator) |
| `poweroff` | | Power off headphones remotely (hardware: experimental) |
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

To send experimental (unverified) commands such as EQ and power-off to real hardware:
```bash
export TUNEDECK_EXPERIMENTAL=1
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
