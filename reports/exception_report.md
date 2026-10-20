# TuneDeck Exception Coverage & Fault Injection Report

## Summary

- **Total Fault Scenarios Tested**: 20
- **Handled Gracefully**: 20
- **Unhandled / Crashes**: 0
- **Bare `except:` Found**: 0
- **Swallowed Exceptions Found**: 17

## Static AST Codebase Scan

### Bare `except:` Statements
✓ **None found.** Zero bare `except:` statements exist in `jblpc/`.

### Swallowed Exceptions (`except Exception: pass`)
- `jblpc/tui/app.py:353` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:431` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:743` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:748` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:753` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:759` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:765` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:770` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:775` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:795` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:830` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:837` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:844` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:851` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:180` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:787` — `NoMatches` (swallowed with pass statement)
- `jblpc/tui/app.py:380` — `NoMatches` (swallowed with pass statement)

## Fault Injection Verification Matrix

| ID | Scenario | Exception Type | Injection Point | Where Caught | User-Visible Message | Exit Code | Status |
|---|---|---|---|---|---|---|---|
| 1 | **Bluetooth adapter off or missing** | `BluetoothAdapterError` | `jblpc.protocol.check_bluetooth_adapter_powered` | `jblpc/cli.py:738, jblpc/controller.py:217` | ✗ Error: Bluetooth adapter is powered off or missing. | `1` | **PASS** |
| 2 | **bluetoothctl not installed** | `BluetoothAdapterError (from FileNotFoundError)` | `jblpc.protocol.check_bluetoothctl_available` | `jblpc/cli.py:738, jblpc/controller.py:217` | ✗ Error: bluetoothctl utility is not installed on this system. | `1` | **PASS** |
| 3 | **Device not paired** | `DeviceNotPairedError` | `jblpc.protocol.check_device_paired` | `jblpc/controller.py:224, jblpc/cli.py:739` | ✗ Error: Device AA:BB:CC:DD:EE:FF is not paired via Bluetooth. | `1` | **PASS** |
| 4 | **Invalid or missing MAC address** | `JBLConnectionError` | `jblpc.protocol.is_valid_mac / controller.connect` | `jblpc/controller.py:205-212` | ✗ Error: No Bluetooth address configured / Invalid Bluetooth MAC address | `1` | **PASS** |
| 5 | **Corrupt or empty config.json** | `ConfigError` | `jblpc.protocol.load_config` | `jblpc/cli.py:737, jblpc/__main__.py:71` | ✗ Error: Configuration file ... is empty / Corrupt configuration file | `1` | **PASS** |
| 6 | **Missing config directory** | `None (Handled gracefully with defaults)` | `jblpc.protocol.load_config / save_config` | `jblpc/protocol.py:280, 313` | Auto-creates directory hierarchy ~/.config/jblpc | `0` | **PASS** |
| 7 | **Connection refused** | `ConnectionRefusedError` | `socket.socket.connect / BluetoothConnection.connect` | `jblpc/protocol.py:368, jblpc/controller.py:247` | ✗ Error: Connection refused by AA:BB:CC:DD:EE:FF on RFCOMM channel 21 | `1` | **PASS** |
| 8 | **Connect timeout** | `TimeoutError / socket.timeout` | `socket.socket.connect / BluetoothConnection.connect` | `jblpc/protocol.py:372, jblpc/controller.py:247` | ✗ Error: Connection timeout after 5.0s connecting to AA:BB:CC:DD:EE:FF | `1` | **PASS** |
| 9 | **Read timeout** | `socket.timeout` | `socket.socket.recv / BluetoothConnection.receive` | `jblpc/protocol.py:430-432` | None (non-blocking loop returns available frames; socket stays clean) | `0` | **PASS** |
| 10 | **Disconnect mid-command** | `EOF / b'' received` | `socket.socket.recv / BluetoothConnection.receive` | `jblpc/protocol.py:425-428` | ✗ Remote device disconnected unexpectedly mid-session. | `1` | **PASS** |
| 11 | **Partial frame** | `Incomplete buffer (< total length)` | `jblpc.protocol.parse_frames` | `jblpc/protocol.py:236-237` | None (retains remainder buffer and awaits next packet) | `0` | **PASS** |
| 12 | **Bad checksum** | `ProtocolError` | `jblpc.protocol.parse_frames (verify_checksum_byte=True)` | `jblpc/protocol.py:247, jblpc/cli.py:741` | ✗ Error: Frame checksum mismatch: expected 0xXX, got 0xYY | `1` | **PASS** |
| 13 | **Unexpected response opcode** | `ProtocolError` | `jblpc.protocol.BluetoothConnection.send_and_receive` | `jblpc/protocol.py:460, jblpc/cli.py:741` | ✗ Error: Unexpected response opcode: expected 0xXXXX, got 0xYYYY | `1` | **PASS** |
| 14 | **Command unsupported by model** | `UnsupportedCommandError` | `jblpc.controller.HeadsetController capability guards` | `jblpc/controller.py:276-291, 517-526` | ✗ Error: ANC / Power off / Equalizer is not supported on <model>. | `1` | **PASS** |
| 15 | **Permission denied on socket** | `PermissionError` | `socket.socket / BluetoothConnection.connect` | `jblpc/protocol.py:364, jblpc/controller.py:247` | ✗ Error: Permission denied accessing Bluetooth socket: [Errno 13] | `1` | **PASS** |
| 16 | **Concurrent second instance** | `InstanceLockError` | `jblpc.lock.SingleInstanceLock.acquire` | `jblpc/cli.py:743` | ✗ Error: Another instance of TuneDeck (jblpc) is already running (locked by ...). | `1` | **PASS** |
| 17 | **KeyboardInterrupt (Ctrl+C)** | `KeyboardInterrupt` | `Top-level CLI execution loop` | `jblpc/cli.py:733, jblpc/__main__.py:69` | Operation cancelled by user. | `130` | **PASS** |
| 18 | **SIGTERM handling** | `SIGTERM signal` | `Operating system process signal` | `Python standard runtime signal handler` | Process terminated cleanly (exit code 143) | `143` | **PASS** |
| 19 | **Terminal too small for TUI** | `TerminalTooSmallError / Layout Notice` | `jblpc.tui.app.JBLPcApp.on_mount` | `jblpc/tui/app.py:870-877` | Terminal size is small. Layout may be compressed. (TUI stays alive) | `0` | **PASS** |
| 20 | **Non-UTF8 device name** | `UnicodeDecodeError (prevented)` | `jblpc.protocol.find_jbl_devices` | `jblpc/protocol.py:485, 502, 525, 544 (errors='replace')` | Replaces invalid byte sequences with Unicode replacement character U+FFFD | `0` | **PASS** |

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
