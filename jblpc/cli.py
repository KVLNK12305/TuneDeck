"""
CLI interface for JBLPc headset and speaker commands.

Provides robust command handling, exit codes, and clean one-line error reporting
without raw tracebacks.
"""

import sys
import json
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .controller import HeadsetController
from .protocol import (
    NoiseMode,
    EQPreset,
    EQ_PRESET_NAMES,
    load_config,
    find_jbl_devices,
    is_valid_mac,
)
from .models import list_supported_models
from .health import BatteryHealthTracker
from .lock import SingleInstanceLock
from .exceptions import (
    JBLPcError,
    ConfigError,
    BluetoothAdapterError,
    DeviceNotPairedError,
    ConnectionError as JBLConnectionError,
    ProtocolError,
    UnsupportedCommandError,
    InstanceLockError,
)

console = Console()


def print_banner():
    """Print the JBL branding banner."""
    banner = Text.from_markup(
        "[bold #FF6600]"
        "     ██╗██████╗ ██╗         ██████╗  ██████╗\n"
        "     ██║██╔══██╗██║         ██╔══██╗██╔════╝\n"
        "     ██║██████╔╝██║         ██████╔╝██║     \n"
        "██   ██║██╔══██╗██║         ██╔═══╝ ██║     \n"
        "╚█████╔╝██████╔╝███████╗    ██║     ╚██████╗\n"
        " ╚════╝ ╚═════╝ ╚══════╝    ╚═╝      ╚═════╝\n"
        "[/]"
        "[dim]    Universal Controller · Linux Edition[/]"
    )
    console.print(Panel(banner, border_style="#FF6600", padding=(0, 2)))


def cmd_status(controller: HeadsetController, json_output: bool = False) -> int:
    """Show device status."""
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect to device'}")
        return 1

    status = controller.get_status_dict()

    if json_output:
        console.print(json.dumps(status, indent=2))
        return 0

    table = Table(
        title="[bold #FF6600]🎧 JBL Device Status[/]",
        border_style="#333333",
        show_header=False,
        pad_edge=True,
        padding=(0, 2),
    )
    table.add_column("Property", style="bold #FF6600", min_width=18)
    table.add_column("Value", style="white")

    table.add_row("Device Model", f"[bold white]{status['device']}[/]")
    table.add_row("Category", status["category"])
    table.add_row("Connected", "[green]Yes[/]" if status["connected"] else "[red]No[/]")

    if status.get("battery_scheme") == "tws_trio":
        table.add_row("Left Earbud", f"[green]{status['battery_left']}%[/]" if status['battery_left'] >= 0 else "Unknown")
        table.add_row("Right Earbud", f"[green]{status['battery_right']}%[/]" if status['battery_right'] >= 0 else "Unknown")
        table.add_row("Charging Case", f"[cyan]{status['battery_case']}%[/]" if status['battery_case'] >= 0 else "Unknown")
    else:
        table.add_row("Battery", f"{status['battery']}%" if status["battery"] >= 0 else "Unknown")

    if status.get("has_anc"):
        table.add_row("Noise Mode", status["noise_mode"])
    else:
        table.add_row("Noise Mode", "[dim]Not supported on this model[/]")

    table.add_row("EQ Type", status.get("eq_type", "Unknown"))
    table.add_row("EQ Preset", status["eq_preset"])
    table.add_row("Address", status["address"] or "Not set")
    table.add_row("Firmware", status["firmware"])

    if status.get("simulating"):
        table.add_row("Mode", "[yellow]Simulation[/]")

    console.print(table)
    return 0


def cmd_models(controller: HeadsetController) -> int:
    """List all supported JBL models across categories."""
    models = list_supported_models()
    table = Table(
        title="[bold #FF6600]📋 Catalog of Supported JBL Devices[/]",
        border_style="#333333",
        padding=(0, 1),
    )
    table.add_column("Model Name", style="bold white", min_width=20)
    table.add_column("Category", style="yellow")
    table.add_column("Protocol", style="cyan")
    table.add_column("ANC", style="green")
    table.add_column("EQ System", style="magenta")
    table.add_column("Battery Scheme", style="blue")

    for m in models:
        anc_str = "✓ Yes" if m.has_anc else "[dim]No[/]"
        table.add_row(
            m.display_name,
            m.category.value.split(" ")[0],
            "Airoha" if "Airoha" in m.protocol_family.value else "Portable",
            anc_str,
            m.eq_type.value,
            "L/R/Case" if m.battery_scheme.value == "tws_trio" else "Single",
        )
    console.print(table)
    console.print(f"[dim]Total cataloged models: {len(models)} · Automatic fallback enabled for uncataloged JBL devices[/]")
    return 0


def cmd_anc(controller: HeadsetController) -> int:
    """Enable ANC."""
    p = controller.state.profile
    if not p.has_anc:
        console.print(f"[red]✗ Error:[/] Active Noise Cancellation is not supported on {p.display_name}.")
        return 1
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1
    if not controller.set_noise_mode(NoiseMode.ANC):
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to enable ANC'}")
        return 1
    console.print("[green]✓[/] ANC [bold]enabled[/]")
    return 0


def cmd_ambient(controller: HeadsetController) -> int:
    """Enable Ambient Aware."""
    p = controller.state.profile
    if not p.has_ambient_aware:
        console.print(f"[red]✗ Error:[/] Ambient Aware is not supported on {p.display_name}.")
        return 1
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1
    if not controller.set_noise_mode(NoiseMode.AMBIENT_AWARE):
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to enable Ambient Aware'}")
        return 1
    console.print("[green]✓[/] Ambient Aware [bold]enabled[/]")
    return 0


def cmd_talkthru(controller: HeadsetController) -> int:
    """Enable TalkThru."""
    p = controller.state.profile
    if not p.has_talkthru:
        console.print(f"[red]✗ Error:[/] TalkThru is not supported on {p.display_name}.")
        return 1
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1
    if not controller.set_noise_mode(NoiseMode.TALKTHRU):
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to enable TalkThru'}")
        return 1
    console.print("[green]✓[/] TalkThru [bold]enabled[/]")
    return 0


def cmd_noiseoff(controller: HeadsetController) -> int:
    """Disable noise control."""
    p = controller.state.profile
    if not (p.has_anc or p.has_ambient_aware or p.has_talkthru):
        console.print(f"[red]✗ Error:[/] Noise control is not supported on {p.display_name}.")
        return 1
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1
    if not controller.set_noise_mode(NoiseMode.OFF):
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to disable noise control'}")
        return 1
    console.print("[green]✓[/] Noise control [bold]disabled[/]")
    return 0


def cmd_battery(controller: HeadsetController) -> int:
    """Show battery level."""
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1

    level = controller.get_battery()
    scheme = controller.state.profile.battery_scheme.value

    if scheme == "tws_trio":
        l = controller.state.battery_left
        r = controller.state.battery_right
        c = controller.state.battery_case
        console.print(f"🔋 TWS Battery: Left: [green]{l}%[/]  Right: [green]{r}%[/]  Case: [cyan]{c}%[/]")
        return 0

    if level >= 0:
        color = "green" if level > 60 else ("yellow" if level > 25 else "red")
        console.print(f"🔋 Battery: [{color}]{level}%[/]")
        return 0
    else:
        console.print("[dim]🔋 Battery: Unknown[/]")
        return 1


def cmd_poweroff(controller: HeadsetController) -> int:
    """Power off headset."""
    p = controller.state.profile
    if not p.has_power_off_command:
        console.print(f"[red]✗ Error:[/] Remote power-off is not supported on {p.display_name} (earbuds power off automatically in charging case).")
        return 1
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1
    if not controller.power_off():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to send power off command'}")
        return 1
    console.print("[green]✓[/] Power off command sent")
    return 0


def cmd_scan(controller: HeadsetController) -> int:
    """Scan for paired JBL devices."""
    console.print("[bold #FF6600]🔍 Scanning for JBL devices...[/]")
    devices = find_jbl_devices()
    if devices:
        table = Table(border_style="#333333")
        table.add_column("Name", style="white")
        table.add_column("Address", style="#FF6600")
        for d in devices:
            table.add_row(d["name"], d["address"])
        console.print(table)
    else:
        console.print("[dim]No paired JBL devices found (pair your device via Bluetooth settings and try again).[/]")
    return 0


def cmd_diagnose(controller: HeadsetController) -> int:
    """Run diagnostics on paired Bluetooth devices and export a device profile report."""
    console.print("[bold #FF6600]🔬 Running JBLPc Device Diagnostics...[/]")
    devices = find_jbl_devices()
    if not devices:
        console.print("[yellow]No paired JBL devices found.[/]")
        console.print("[dim]Pair your JBL device via Bluetooth settings and run this command again.[/]")
        return 1

    console.print(f"[green]Found {len(devices)} JBL device(s):[/]")
    for dev in devices:
        addr = dev["address"]
        name = dev["name"]
        console.print(f"  • [bold white]{name}[/] ({addr})")

    target = devices[0]
    dump_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "device_name": target["name"],
        "bluetooth_address": target["address"],
        "detected_profile": controller.state.profile.model_id,
        "diagnostics_status": "READY_FOR_COMMUNITY_SUBMISSION",
    }
    dump_file = Path("jbl_device_diagnostic.json")
    try:
        with open(dump_file, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)
        console.print(f"\n[green]✓ Diagnostic dump exported to:[/] [bold]{dump_file}[/]")
        console.print("[dim]You can share this JSON file on GitHub to contribute support for this model.[/]")
        return 0
    except OSError as e:
        console.print(f"[red]Error saving dump:[/] {e}")
        return 1


def _print_eq_visualizer(controller: HeadsetController, selected_idx: Optional[int] = None):
    """Render an ASCII/Rich EQ curve and frequency bar display."""
    p = controller.state.profile
    bands = controller.state.eq_bands
    freqs = p.eq_band_frequencies

    console.print()
    console.print(f"[bold #FF6600]🎚️ Equalizer — {p.display_name}[/] [dim]({p.eq_type.value.upper()})[/]")
    console.print(f"  Active Preset: [bold white]{controller.state.eq_preset_name}[/]")
    console.print()

    # If in interactive mode, display cursor pointer row above bands
    if selected_idx is not None:
        pointer_row = ["        "]
        for i in range(len(bands)):
            pointer = "  ▼  " if i == selected_idx else "     "
            pointer_row.append(f"[bold #FF6600]{pointer}[/]")
        console.print("".join(pointer_row))

    # Step through dB range +12 to -12 in 3dB increments
    for step in range(12, -13, -3):
        row = [f"{step:+3d}dB │"]
        for i, val in enumerate(bands):
            is_active = (selected_idx is not None and i == selected_idx)
            if step > 0:
                char = "█" if val >= step else "·"
                color = "#FF8833" if val >= step else ("#555555" if is_active else "#333333")
            elif step == 0:
                char = "█" if val == 0 else "─"
                color = "#00FF88" if val == 0 else "#666666"
            else:
                char = "█" if val <= step else "·"
                color = "#3388FF" if val <= step else ("#555555" if is_active else "#333333")
            row.append(f"[{color}]{char:^5}[/]")
        console.print("".join(row))

    console.print("       └" + ("─────" * len(freqs)))
    freq_row = ["        "]
    for i, f in enumerate(freqs):
        if selected_idx is not None and i == selected_idx:
            freq_row.append(f"[bold black on #FF6600]{f:^5}[/]")
        else:
            freq_row.append(f"[bold #FF6600]{f:^5}[/]")
    console.print("".join(freq_row))

    gain_row = ["        "]
    for i, g in enumerate(bands):
        color = "green" if g == 0 else ("yellow" if g > 0 else "cyan")
        if selected_idx is not None and i == selected_idx:
            gain_row.append(f"[bold white]{g:+3d}dB[/] ")
        else:
            gain_row.append(f"[{color}]{g:+3d}dB[/] ")
    console.print("".join(gain_row))
    console.print()


def interactive_eq(controller: HeadsetController) -> int:
    """Run interactive terminal EQ tuner with W, A, S, D and Ctrl+S to save."""
    if not sys.stdin.isatty():
        console.print("[red]✗ Error:[/] Interactive EQ mode requires an interactive TTY terminal.")
        return 1

    import tty
    import termios
    import select

    p = controller.state.profile
    bands = list(controller.state.eq_bands)
    selected = 0
    num_bands = len(bands)

    old_settings = termios.tcgetattr(sys.stdin)
    console.print("\n[bold #FF6600]🎚️ Interactive Equalizer Tuning[/]")
    console.print("[dim]Use [bold white]A/D[/] to select band, [bold white]W/S[/] to change gain, [bold white]Ctrl+S[/] to save, [bold white]Q[/] to quit.[/]\n")

    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            _print_eq_visualizer(controller, selected_idx=selected)
            console.print(
                f"[bold white]Active Band: [bold yellow]{p.eq_band_frequencies[selected]}[/] ({bands[selected]:+d}dB) "
                f"| [dim]A/D: select · W/S: ±gain · Ctrl+S: save & apply · Q: exit[/]"
            )

            ch = sys.stdin.read(1)
            if ch == "\x1b":  # Escape sequence
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    seq = sys.stdin.read(2)
                    if seq == "[A":
                        ch = "w"
                    elif seq == "[B":
                        ch = "s"
                    elif seq == "[C":
                        ch = "d"
                    elif seq == "[D":
                        ch = "a"
                else:
                    break  # Bare Escape key

            if ch.lower() == "a":
                selected = max(0, selected - 1)
            elif ch.lower() == "d":
                selected = min(num_bands - 1, selected + 1)
            elif ch.lower() == "w":
                bands[selected] = min(12, bands[selected] + 1)
                controller.set_eq_bands(bands)
            elif ch.lower() == "s":
                bands[selected] = max(-12, bands[selected] - 1)
                controller.set_eq_bands(bands)
            elif ch == "\x13":  # Ctrl+S
                controller.set_eq_bands(bands)
                controller.save_eq_to_config()
                console.print("\n[bold green]✓ Equalizer saved to config.json and applied to headset![/]\n")
                return 0
            elif ch.lower() == "q" or ch == "\x03":  # Q or Ctrl+C
                console.print("\n[yellow]Interactive EQ closed without saving.[/]\n")
                return 0
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def cmd_eq(controller: HeadsetController, args: list[str], json_output: bool = False) -> int:
    """View or customize equalizer presets and band gain levels."""
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1

    p = controller.state.profile
    if p.eq_type.value == "none" or not p.eq_band_frequencies:
        console.print(f"[red]✗ Error:[/] Equalizer is not supported on {p.display_name}.")
        return 1

    # Check for --save flag
    should_save = "--save" in args
    if should_save:
        args = [a for a in args if a != "--save"]

    if args:
        target = args[0].lower()

        if target in ("-i", "--interactive", "edit"):
            return interactive_eq(controller)

        if target == "save":
            if controller.save_eq_to_config():
                console.print("[green]✓[/] Saved active EQ preset and band levels to config.json")
                return 0
            else:
                console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to save EQ'}")
                return 1

        preset_lookup = {
            "flat": EQPreset.FLAT,
            "jazz": EQPreset.JAZZ,
            "vocal": EQPreset.VOCAL,
            "bass": EQPreset.BASS,
            "bass-boost": EQPreset.BASS,
            "club": EQPreset.CLUB,
        }

        if target in preset_lookup:
            preset = preset_lookup[target]
            if controller.set_eq_preset(preset):
                if should_save:
                    controller.save_eq_to_config()
                console.print(f"[green]✓[/] EQ preset set to [bold #FF6600]{EQ_PRESET_NAMES.get(preset, target)}[/]")
                if should_save:
                    console.print("[green]✓[/] Equalizer configuration saved to config.json")
                if not json_output:
                    _print_eq_visualizer(controller)
                return 0
            else:
                console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to set EQ preset'}")
                return 1

        # Check for band values: `eq 2 1 0 -1 ...` or `eq --bands 2,1,0,...`
        band_tokens = []
        if target == "--bands" and len(args) > 1:
            band_tokens = args[1].replace(",", " ").split()
        elif target.startswith("--bands="):
            band_tokens = target.split("=", 1)[1].replace(",", " ").split()
        elif all(tok.lstrip("+-").isdigit() for tok in args):
            band_tokens = args

        if band_tokens:
            try:
                values = [int(v) for v in band_tokens]
            except ValueError:
                console.print("[red]✗ Error:[/] Band gain values must be integers between -12 and +12 dB.")
                return 1

            expected = len(p.eq_band_frequencies)
            if len(values) != expected:
                console.print(f"[red]✗ Error:[/] {p.display_name} requires {expected} bands, but received {len(values)}.")
                return 1

            if controller.set_eq_bands(values):
                if should_save:
                    controller.save_eq_to_config()
                console.print(f"[green]✓[/] Custom EQ bands applied: [bold]{values}[/]")
                if should_save:
                    console.print("[green]✓[/] Equalizer configuration saved to config.json")
                if not json_output:
                    _print_eq_visualizer(controller)
                return 0
            else:
                console.print(f"[red]✗ Error:[/] {controller.last_error or 'Failed to set custom EQ bands'}")
                return 1

        console.print(f"[red]✗ Error:[/] Unknown EQ option '{target}'. Available: -i/--interactive, save, flat, jazz, vocal, bass, club (or provide {len(p.eq_band_frequencies)} band values).")
        return 1

    if json_output:
        out = {
            "device_id": controller.state.bt_address or controller.state.device_name,
            "device_name": p.display_name,
            "eq_type": p.eq_type.value,
            "preset": controller.state.eq_preset_name,
            "bands": [
                {"freq": freq, "gain_db": gain}
                for freq, gain in zip(p.eq_band_frequencies, controller.state.eq_bands)
            ],
        }
        print(json.dumps(out, indent=2))
        return 0

    _print_eq_visualizer(controller)
    return 0


def cmd_health(controller: HeadsetController, json_output: bool = False) -> int:
    """Display estimated battery health overview (retention trend & equivalent full cycles)."""
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1

    tracker = BatteryHealthTracker()
    tracker.log_state(controller.state)

    device_id = controller.state.bt_address or controller.state.device_name
    report = tracker.get_health_summary(device_id, controller.state.device_name)

    if json_output:
        out = {
            "device_id": report.device_id,
            "device_name": report.device_name,
            "timestamp": report.timestamp,
            "components": {},
        }
        for comp_name, comp in report.components.items():
            out["components"][comp_name] = {
                "current_level": comp.current_level,
                "readings_count": comp.readings_count,
                "data_span_days": comp.data_span_days,
                "estimated_cycles": comp.estimated_cycles,
                "discharge_rate_pct_per_hr": comp.discharge_rate_pct_per_hr,
                "retention_trend_pct": comp.retention_trend_pct,
                "confidence": comp.confidence,
                "note": comp.note,
            }
        print(json.dumps(out, indent=2))
        return 0

    console.print()
    table = Table(
        title=f"[bold #FF6600]🔋 Estimated Battery Health Overview — {report.device_name}[/]",
        border_style="#333333",
        padding=(0, 2),
    )
    table.add_column("Component", style="bold white", min_width=12)
    table.add_column("Level", style="green")
    table.add_column("Est. Cycles", style="yellow")
    table.add_column("Discharge Rate", style="cyan")
    table.add_column("Est. Retention", style="magenta")
    table.add_column("Data Span", style="blue")
    table.add_column("Confidence", style="bold")

    for comp_name, comp in report.components.items():
        conf_color = "red" if comp.confidence == "low" else ("yellow" if comp.confidence == "medium" else "green")
        rate_str = f"{comp.discharge_rate_pct_per_hr:.1f}%/hr" if comp.discharge_rate_pct_per_hr else "N/A"
        ret_str = f"{comp.retention_trend_pct:.1f}%" if comp.retention_trend_pct else "N/A"

        table.add_row(
            comp_name.capitalize(),
            f"{comp.current_level}%" if comp.current_level >= 0 else "N/A",
            f"{comp.estimated_cycles:.1f} EFC",
            rate_str,
            ret_str,
            f"{comp.data_span_days:.1f} days",
            f"[{conf_color}]{comp.confidence.upper()}[/]",
        )

    console.print(table)
    console.print()
    for comp_name, comp in report.components.items():
        console.print(f"[dim]• {comp_name.capitalize()}: {comp.note}[/]")
    console.print()
    console.print("[dim italic]Notice: Values are mathematical estimates derived from usage history, NOT true hardware state-of-health.[/]")
    return 0


def cmd_battery_log(controller: HeadsetController, interval: float = 0.0, count: int = 1) -> int:
    """Log current battery reading to the SQLite health database."""
    if not controller.connect():
        console.print(f"[red]✗ Error:[/] {controller.last_error or 'Could not connect'}")
        return 1

    tracker = BatteryHealthTracker()

    for i in range(count):
        logged = tracker.log_state(controller.state)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        device = controller.state.device_name
        console.print(f"[green]✓[/] [{now_str}] Logged battery reading for {device}: components={logged}")

        if i + 1 < count and interval > 0:
            time.sleep(interval)
            controller.get_battery()

    return 0


def cmd_help():
    """Show help."""
    print_banner()
    console.print()
    table = Table(
        title="[bold #FF6600]Available Commands[/]",
        border_style="#333333",
        padding=(0, 2),
    )
    table.add_column("Command", style="bold white", min_width=14)
    table.add_column("Description", style="dim")

    commands = [
        ("status", "Show headset/speaker status"),
        ("models", "List all supported JBL models"),
        ("health", "Show estimated battery health, cycles & retention trend (--json supported)"),
        ("battery-log", "Record battery reading into SQLite health database"),
        ("eq", "View or customize equalizer presets & band gains (--json, preset, or --bands)"),
        ("anc", "Enable Active Noise Cancellation"),
        ("ambient", "Enable Ambient Aware"),
        ("talkthru", "Enable TalkThru mode"),
        ("noiseoff", "Disable noise control"),
        ("battery", "Check battery level (Single or Left/Right/Case)"),
        ("poweroff", "Power off headset remotely"),
        ("scan", "Scan for paired JBL devices"),
        ("diagnose", "Run diagnostics & export report for unsupported model"),
    ]
    for name, desc in commands:
        table.add_row(name, desc)

    console.print(table)
    console.print()
    console.print("[dim]Set your device address: export JBL_BD=\"XX:XX:XX:XX:XX:XX\" (or TUNEDECK_BD)[/]")
    console.print("[dim]Run simulation mode:     tunedeck cli --sim status[/]")
    console.print("[dim]Simulate specific model: tunedeck cli --sim --model \"JBL Flip 6\" status[/]")


def run_cli(args: list[str]) -> int:
    """
    Run a CLI command with robust error handling and exit codes.
    Returns process exit code (0 for success, non-zero for error).
    """
    if not args or args[0] in ("help", "--help", "-h"):
        cmd_help()
        return 0

    try:
        # Check for simulation flag
        simulate = "--sim" in args
        args = [a for a in args if a != "--sim"]

        # Check for json flag
        json_output = "--json" in args
        args = [a for a in args if a != "--json"]

        # Check for interval flag
        interval = 0.0
        if "--interval" in args:
            idx = args.index("--interval")
            if idx + 1 < len(args):
                try:
                    interval = float(args[idx + 1])
                except ValueError:
                    console.print("[red]✗ Error:[/] --interval must be a numeric value in seconds.")
                    return 1
                args = args[:idx] + args[idx + 2:]

        # Check for count flag
        count = 1
        if "--count" in args:
            idx = args.index("--count")
            if idx + 1 < len(args):
                try:
                    count = int(args[idx + 1])
                except ValueError:
                    console.print("[red]✗ Error:[/] --count must be an integer.")
                    return 1
                args = args[:idx] + args[idx + 2:]

        # Check for model flag
        model_name = None
        if "--model" in args:
            idx = args.index("--model")
            if idx + 1 < len(args):
                model_name = args[idx + 1]
                args = args[:idx] + args[idx + 2:]

        if not args:
            cmd_help()
            return 0

        command = args[0].lower()

        # Load config safely
        config = load_config()
        bt_address = None

        if not simulate:
            try:
                from .protocol import get_active_jbl_device
                from .models import match_device_profile
                active_dev = get_active_jbl_device()
                if active_dev and active_dev.get("address"):
                    bt_address = active_dev["address"]
                    if not model_name and active_dev.get("name"):
                        matched = match_device_profile(active_dev["name"])
                        if matched:
                            model_name = matched.model_id
            except Exception:
                pass

        if not bt_address:
            bt_address = config.get("bluetooth_address", "")

        with SingleInstanceLock():
            controller = HeadsetController(
                bt_address=bt_address,
                simulate=simulate,
                model=model_name,
            )

            if command == "status":
                return cmd_status(controller, json_output=json_output)
            elif command == "models":
                return cmd_models(controller)
            elif command == "health":
                return cmd_health(controller, json_output=json_output)
            elif command == "battery-log":
                return cmd_battery_log(controller, interval=interval, count=count)
            elif command == "eq":
                return cmd_eq(controller, args[1:], json_output=json_output)
            elif command == "anc":
                return cmd_anc(controller)
            elif command == "ambient":
                return cmd_ambient(controller)
            elif command == "talkthru":
                return cmd_talkthru(controller)
            elif command == "noiseoff":
                return cmd_noiseoff(controller)
            elif command == "battery":
                return cmd_battery(controller)
            elif command == "poweroff":
                return cmd_poweroff(controller)
            elif command == "scan":
                return cmd_scan(controller)
            elif command == "diagnose":
                return cmd_diagnose(controller)
            else:
                console.print(f"[red]✗ Error:[/] Unknown command '{command}'. Run 'tunedeck cli help' for available commands.")
                return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/]")
        return 130
    except (
        ConfigError,
        BluetoothAdapterError,
        DeviceNotPairedError,
        JBLConnectionError,
        ProtocolError,
        UnsupportedCommandError,
        InstanceLockError,
    ) as e:
        console.print(f"[red]✗ Error:[/] {e}")
        return 1
    except Exception as e:
        console.print(f"[red]✗ Error:[/] {e}")
        return 1
