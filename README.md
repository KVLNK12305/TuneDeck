<p align="center">
  <img src="assets/logo.png" alt="TuneDeck Logo" width="220">
</p>


# TuneDeck

A terminal, desktop, and CLI controller for JBL headphones that use the Airoha RACE protocol over Bluetooth RFCOMM.

> Independent project. Not affiliated with or endorsed by JBL, Harman, or Samsung. Trademarks belong to their owners.

## Status

Tested on real hardware: Linux (maintainer) and Windows 11 (community tester). Everything else is untested or simulated.

| Feature | Status |
|---|---|
| Noise control (ANC / Ambient / TalkThru / Off) | Works on real hardware. Mode changes made on the headset are picked up. |
| Battery level | Works, read from the OS Bluetooth stack (BlueZ/UPower). RACE battery query is an unverified fallback. |
| Equalizer | Experimental. Opcode and payload unverified, no ACK read. Needs `TUNEDECK_EXPERIMENTAL=1`. |
| Remote power-off | Experimental. Opcode unverified. Needs `TUNEDECK_EXPERIMENTAL=1`. |
| TWS left/right/case battery | Not decoded. Simulator only. |
| Firmware version | Not read. |
| Speakers / PartyBox | Different protocol, not implemented. Simulator only. |

| OS | Hardware control |
|---|---|
| Linux | Yes (BlueZ, RFCOMM channel 21) |
| Windows | Community tested |
| macOS | Currently untested |

## Install

Requires Python 3.10+. On Linux you need BlueZ running and your user in the `bluetooth` group. The GUI on X11 also needs `libxcb-cursor0`.

```bash
git clone https://github.com/KVLNK12305/TuneDeck.git
cd TuneDeck
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[gui]"
```

Pair your headphones in your system Bluetooth settings first.

## Usage

```bash
tunedeck              # terminal UI
tunedeck-gui          # desktop UI (Qt6 / PySide6)
tunedeck cli status   # scriptable CLI
```

Add `--sim --model "JBL Tune 770NC"` to any of them to run without hardware.

### CLI commands

| Command | Description |
|---|---|
| `status [--json]` | Connection state, model, noise mode, battery |
| `anc` / `ambient` / `talkthru` / `noiseoff` | Set noise mode |
| `battery` | Battery level |
| `eq [preset or bands...] [--save]` | View or set EQ (hardware is experimental) |
| `poweroff` | Power off headphones (experimental) |
| `scan` | List paired JBL devices |
| `models` | List model profiles |
| `diagnose` | Dump diagnostics for an uncataloged device |

```bash
tunedeck cli eq bass --save
tunedeck cli eq 5 4 3 2 1 0 -1 -2 -3 -4   # gains in dB, -12 to +12
```

### TUI keys

`q` quit, `c`/`x` connect/disconnect, `n` cycle noise mode, `1`-`4` pick noise mode, `e` cycle EQ preset, arrows or `a`/`d`/`w`/`s` edit EQ bands, `Ctrl+S` save EQ, `b` refresh battery, `h` battery health, `p` power off, `m` toggle sim/hardware.

## Model profiles

The catalog has 30 JBL models. Profiles decide which controls the UI shows and are built from public product specs, **not tested per model**. Over-ear and TWS models are marked as Airoha RACE; portable speakers and PartyBox models are simulator-only. Run `tunedeck cli models` for the full list.

If you own a JBL headset and try this, please open an issue with your model and what worked. `tunedeck cli diagnose` output helps.

## Configuration

Config lives in `~/.config/tunedeck/config.json` (Linux), `~/Library/Application Support/tunedeck/` (macOS), or `%APPDATA%\tunedeck\` (Windows).

- `JBL_BD="AA:BB:CC:DD:EE:FF"` selects a specific device.
- `TUNEDECK_EXPERIMENTAL=1` enables unverified commands (EQ, power-off).

## Tests

```bash
pytest -q -m "not hardware"
```

## License

MIT
