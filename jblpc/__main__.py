"""
TuneDeck entry point.

Usage:
    python -m jblpc              # Launch TUI (default)
    tunedeck                     # Launch TUI
    tunedeck --sim               # Launch TUI in simulation mode
    tunedeck cli <cmd>           # CLI mode
    tunedeck cli --sim <cmd>     # CLI simulation mode
"""

import sys
from .protocol import load_config
from .controller import HeadsetController


def main():
    args = sys.argv[1:]

    # Check for simulation flag
    simulate = "--sim" in args
    args = [a for a in args if a != "--sim"]

    # Check for model flag
    model_name = None
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model_name = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

    # GUI mode (e.g. `tunedeck gui` or `tunedeck --gui`)
    if "--gui" in args or (args and args[0] == "gui"):
        from tunedeck_gui.__main__ import main as gui_main
        gui_args = [a for a in args if a not in ("--gui", "gui")]
        if simulate:
            gui_args.append("--sim")
        if model_name:
            gui_args.extend(["--model", model_name])
        sys.exit(gui_main(gui_args))

    # CLI mode
    if args and args[0] == "cli":
        from .cli import run_cli
        cli_args = list(args[1:])
        if simulate:
            cli_args.append("--sim")
        if model_name:
            cli_args.extend(["--model", model_name])
        code = run_cli(cli_args)
        sys.exit(code)

    # TUI mode (default)
    try:
        config = load_config()
        bt_address = config.get("bluetooth_address", "")

        # Auto-discover paired JBL device if not set
        if not bt_address and not simulate:
            try:
                from .protocol import find_jbl_devices
                paired = find_jbl_devices()
                if paired:
                    bt_address = paired[0]["address"]
            except Exception:
                pass

        # If no address found and no simulation, launch simulation mode directly
        if not bt_address and not simulate:
            from rich.console import Console
            console = Console()
            console.print("[dim]No Bluetooth address configured. Launching in simulation mode...[/]")
            simulate = True

        controller = HeadsetController(bt_address=bt_address, simulate=simulate, model=model_name)

        from .tui.app import run_tui
        run_tui(controller)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        from rich.console import Console
        Console(stderr=True).print(f"[red]✗ Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
