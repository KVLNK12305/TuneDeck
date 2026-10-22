"""
Entry point for TuneDeck Native GUI application.
"""

import sys
import argparse
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
        default=True,
        help="Run in offline simulation mode without physical Bluetooth hardware (default: True)",
    )
    parser.add_argument(
        "--hardware",
        action="store_false",
        dest="sim",
        help="Connect to real hardware via Bluetooth instead of simulator",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="JBL Tune 770NC",
        help="Model profile to load in simulator (default: 'JBL Tune 770NC')",
    )
    parser.add_argument(
        "--address",
        "-b",
        type=str,
        default=None,
        help="Target device Bluetooth MAC address (e.g. AA:BB:CC:DD:EE:FF)",
    )
    return parser.parse_args(args)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    return run_gui(
        simulate=args.sim,
        sim_model=args.model,
        address=args.address,
    )


if __name__ == "__main__":
    sys.exit(main())
