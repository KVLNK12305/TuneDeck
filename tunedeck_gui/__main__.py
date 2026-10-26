"""
Entry point for TuneDeck Native GUI application.
"""

import os
import sys
import argparse
import ctypes.util
from typing import Optional

from .app import run_gui


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tunedeck-gui",
        description="TuneDeck Native GUI — Cross-Platform Desktop Controller for JBL Devices",
    )
    parser.add_argument(
        "--sim",
        action="store_true",
        default=False,
        help="Run in offline simulation mode without physical Bluetooth hardware",
    )
    parser.add_argument(
        "--hardware",
        action="store_false",
        dest="sim",
        help="Connect to real hardware via Bluetooth (the default)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model profile to use (default: detected from the device; 'JBL Tune 770NC' in --sim)",
    )
    parser.add_argument(
        "--address",
        "-b",
        type=str,
        default=None,
        help="Target device Bluetooth MAC address (e.g. AA:BB:CC:DD:EE:FF)",
    )
    return parser.parse_args(args)


def _check_linux_display_libs() -> Optional[str]:
    """Return a hint if Qt can't open a window on Linux/BSD, instead of letting Qt abort.

    Since Qt 6.5 the xcb platform plugin needs libxcb-cursor, which many distros
    (e.g. Ubuntu 22.04) don't install by default.
    """
    if not sys.platform.startswith(("linux", "freebsd", "openbsd", "netbsd")):
        return None
    if os.environ.get("QT_QPA_PLATFORM"):
        return None
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return (
            "TuneDeck GUI needs a graphical desktop session, and none was found "
            "(no DISPLAY or WAYLAND_DISPLAY, e.g. over SSH).\n"
            "Use the terminal UI instead:  tunedeck"
        )
    if ctypes.util.find_library("xcb-cursor"):
        return None
    if os.environ.get("WAYLAND_DISPLAY"):
        # Native Wayland doesn't need libxcb-cursor
        os.environ["QT_QPA_PLATFORM"] = "wayland"
        return None
    return (
        "TuneDeck GUI can't open a window: the system library libxcb-cursor is missing "
        "(required by Qt 6.5+ on X11).\n"
        "Install it, then run tunedeck-gui again:\n"
        "  Ubuntu/Debian:  sudo apt install libxcb-cursor0\n"
        "  Fedora:         sudo dnf install xcb-util-cursor\n"
        "  Arch:           sudo pacman -S xcb-util-cursor\n"
        "Or use the terminal UI instead:  tunedeck"
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    hint = _check_linux_display_libs()
    if hint:
        print(hint, file=sys.stderr)
        return 1
    return run_gui(
        simulate=args.sim,
        model=args.model,
        address=args.address,
    )


if __name__ == "__main__":
    sys.exit(main())
