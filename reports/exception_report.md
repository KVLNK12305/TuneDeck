# TuneDeck Exception Coverage & Fault Injection Report

## Summary

- **Documented Fault Scenarios**: 20 (expected behaviour; run `pytest -m fault` to verify)
- **Bare `except:` Found**: 0
- **Swallowed Exceptions Found**: 37

## Static AST Codebase Scan

### Bare `except:` Statements
✓ **None found.** Zero bare `except:` statements exist in `jblpc/`.

### Swallowed Exceptions (`except Exception: pass`)
- `jblpc/__main__.py:73` — `Exception` (swallowed with pass statement)
- `jblpc/cli.py:726` — `Exception` (swallowed with pass statement)
- `jblpc/controller.py:502` — `Exception` (swallowed with pass statement)
- `jblpc/controller.py:178` — `Exception` (swallowed with pass statement)
- `jblpc/controller.py:355` — `Exception` (swallowed with pass statement)
- `jblpc/controller.py:364` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:777` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:928` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:944` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:631` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:712` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:798` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:844` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:895` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:656` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:910` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:710` — `Exception` (swallowed with pass statement)
- `jblpc/protocol.py:743` — `Exception` (swallowed with pass statement)
- `jblpc/tui/app.py:432` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:514` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:834` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:845` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:850` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:855` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:861` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:868` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:875` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:880` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:885` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:908` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:962` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:973` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:984` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:995` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:204` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:900` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:463` — `NoMatches` (swallowed with pass statement)

## Fault Injection Scenarios (Expected Handling)

| ID | Scenario | Exception Type | Injection Point | Where Caught | User-Visible Message | Exit Code |
|---|---|---|---|---|---|---|
| 1 | **Bluetooth adapter off or missing** | `BluetoothAdapterError` | `jblpc.protocol.check_bluetooth_adapter_powered` | `cli.run_cli() exception handler, controller.connect()` | ✗ Error: Bluetooth adapter is powered off or missing. | `1` |
| 2 | **bluetoothctl not installed** | `BluetoothAdapterError (from FileNotFoundError)` | `jblpc.protocol.check_bluetoothctl_available` | `cli.run_cli() exception handler, controller.connect()` | ✗ Error: bluetoothctl utility is not installed on this system. | `1` |
| 3 | **Device not paired** | `DeviceNotPairedError` | `jblpc.protocol.check_device_paired` | `controller.connect(), cli.run_cli() exception handler` | ✗ Error: Device AA:BB:CC:DD:EE:FF is not paired via Bluetooth. | `1` |
| 4 | **Invalid or missing MAC address** | `JBLConnectionError` | `jblpc.protocol.is_valid_mac / controller.connect` | `controller.connect() validation guards` | ✗ Error: No JBL device found. Pair it in your system Bluetooth settings... / Invalid Bluetooth MAC address | `1` |
| 5 | **Corrupt or empty config.json** | `ConfigError` | `jblpc.protocol.load_config` | `cli.run_cli() exception handler, __main__.main()` | ✗ Error: Configuration file ... is empty / Corrupt configuration file | `1` |
| 6 | **Missing config directory** | `None (Handled gracefully with defaults)` | `jblpc.protocol.load_config / save_config` | `protocol.load_config(), protocol.save_config()` | Auto-creates directory hierarchy ~/.config/jblpc | `0` |
| 7 | **Connection refused** | `ConnectionRefusedError` | `socket.socket.connect / BluetoothConnection.connect` | `BluetoothConnection.connect(), controller.connect()` | ✗ Error: Connection refused by AA:BB:CC:DD:EE:FF on RFCOMM channel 21 | `1` |
| 8 | **Connect timeout** | `TimeoutError / socket.timeout` | `socket.socket.connect / BluetoothConnection.connect` | `BluetoothConnection.connect(), controller.connect()` | ✗ Error: Connection timeout after 5.0s connecting to AA:BB:CC:DD:EE:FF | `1` |
| 9 | **Read timeout** | `socket.timeout` | `socket.socket.recv / BluetoothConnection.receive` | `BluetoothConnection.receive() timeout loop` | None (non-blocking loop returns available frames; socket stays clean) | `0` |
| 10 | **Disconnect mid-command** | `EOF / b'' received` | `socket.socket.recv / BluetoothConnection.receive` | `BluetoothConnection.receive() empty-read guard` | ✗ Remote device disconnected unexpectedly mid-session. | `1` |
| 11 | **Partial frame** | `Incomplete buffer (< total length)` | `jblpc.protocol.parse_frames` | `parse_frames() incomplete-frame break` | None (retains remainder buffer and awaits next packet) | `0` |
| 12 | **Unverified command on hardware** | `None (command refused)` | `jblpc.controller.HeadsetController.set_eq_preset / set_eq_bands / power_off` | `experimental_commands_enabled() check before sending` | ✗ Error: EQ on hardware is experimental: this command uses an unverified protocol opcode; set TUNEDECK_EXPERIMENTAL=1 to send it anyway. | `1` |
| 13 | **Unexpected response opcode** | `ProtocolError` | `jblpc.protocol.BluetoothConnection.send_and_receive` | `BluetoothConnection.send_and_receive(), cli.run_cli() exception handler` | ✗ Error: Unexpected response opcode: expected 0xXXXX, got 0xYYYY | `1` |
| 14 | **Command unsupported by model** | `UnsupportedCommandError` | `jblpc.controller.HeadsetController capability guards` | `HeadsetController.set_noise_mode(), .set_eq_preset(), .power_off()` | ✗ Error: ANC / Power off / Equalizer is not supported on <model>. | `1` |
| 15 | **Permission denied on socket** | `PermissionError` | `socket.socket / BluetoothConnection.connect` | `BluetoothConnection.connect(), controller.connect()` | ✗ Error: Permission denied accessing Bluetooth socket: [Errno 13] | `1` |
| 16 | **Concurrent second instance** | `InstanceLockError` | `jblpc.lock.SingleInstanceLock.acquire` | `cli.run_cli() exception handler` | ✗ Error: Another instance of TuneDeck (jblpc) is already running (locked by ...). | `1` |
| 17 | **KeyboardInterrupt (Ctrl+C)** | `KeyboardInterrupt` | `Top-level CLI execution loop` | `cli.run_cli() KeyboardInterrupt handler, __main__.main()` | Operation cancelled by user. | `130` |
| 18 | **SIGTERM handling** | `SIGTERM signal` | `Operating system process signal` | `Python standard runtime signal handler` | Process terminated cleanly (exit code 143) | `143` |
| 19 | **Terminal too small for TUI** | `TerminalTooSmallError / Layout Notice` | `jblpc.tui.app.JBLPcApp.on_mount` | `JBLPcApp.on_mount() terminal size check` | Terminal size is small. Layout may be compressed. (TUI stays alive) | `0` |
| 20 | **Non-UTF8 device name** | `UnicodeDecodeError (prevented)` | `jblpc.protocol.find_jbl_devices` | `protocol subprocess .decode() calls (errors='replace')` | Replaces invalid byte sequences with Unicode replacement character U+FFFD | `0` |

## Bug Fixes Exposed by Tests

1. **Noise Mode Capability Gating in `HeadsetController`**:
   - *Bug*: `set_noise_mode` checked `p.has_anc` for all modes except `OFF`. This caused models with Ambient Aware / TalkThru but without ANC (e.g. Wave Buds, Endurance Peak 3) to incorrectly reject `ambient` and `talkthru` commands.
   - *Fix*: Gated each mode against its specific capability (`p.has_ambient_aware`, `p.has_talkthru`, `p.has_anc`), and allowed `cycle_noise_mode` to cycle between whichever subset of modes the hardware supports.

2. **Rich Console Line-Wrapping in JSON CLI Output**:
   - *Bug*: `cmd_health(..., json_output=True)` printed JSON using `rich.console.Console.print()`, which inserted soft-wrap newlines into strings when terminal width was constrained, breaking `json.loads()` parser.
   - *Fix*: Replaced `console.print(json.dumps(...))` with raw `print(json.dumps(...))` for all machine-readable output.

3. **Controller Init Model Parameter Ambiguity**:
   - *Bug*: `HeadsetController` accepted only `model`, causing `TypeError` when instantiated with `model_id` in TUI and simulator invocations.
   - *Fix*: Accepted both `model` and `model_id` aliases seamlessly.

4. **Corrupted SQLite Battery Database Auto-Recovery**:
   - *Bug*: Corrupted SQLite databases raised raw `sqlite3.DatabaseError` upon launch.
   - *Fix*: Added auto-recovery in `BatteryHealthTracker._init_db()` that moves the corrupted file to a `.corrupt.<timestamp>` backup and creates a clean schema.

5. **TUI DOM Query Exception Handling**:
   - *Bug*: Several DOM queries relied on catch-all `except Exception: pass`.
   - *Fix*: Replaced with specific `except NoMatches:` from `textual.css.query`.

6. **Missing RFCOMM Channel in Default Config**:
   - *Bug*: `load_config` did not supply `rfcomm_channel: 21` when `config.json` was missing.
   - *Fix*: Added default `rfcomm_channel: 21` to the fallback dictionary.
