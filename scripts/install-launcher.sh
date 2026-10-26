#!/usr/bin/env bash
#
# Make `tunedeck` / `tunedeck-gui` runnable without activating the venv, and add
# TuneDeck to the desktop app menu (Linux, including SteamOS Desktop Mode).
#
# Usage:  scripts/install-launcher.sh            # install
#         scripts/install-launcher.sh --uninstall
#
# Requires the project to be installed in .venv first:
#   python3 -m venv .venv && .venv/bin/pip install -e ".[gui]"

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$REPO_DIR/.venv/bin"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/tunedeck.desktop"

if [ "${1:-}" = "--uninstall" ]; then
    rm -f "$BIN_DIR/tunedeck" "$BIN_DIR/tunedeck-gui" "$DESKTOP_FILE"
    echo "Removed TuneDeck launchers."
    exit 0
fi

for cmd in tunedeck tunedeck-gui; do
    if [ ! -x "$VENV_BIN/$cmd" ]; then
        echo "error: $VENV_BIN/$cmd not found. Install first:" >&2
        echo "  python3 -m venv .venv && .venv/bin/pip install -e \".[gui]\"" >&2
        exit 1
    fi
done

mkdir -p "$BIN_DIR" "$APPS_DIR"

# The venv scripts already point at the venv's Python, so a symlink is enough.
ln -sf "$VENV_BIN/tunedeck" "$BIN_DIR/tunedeck"
ln -sf "$VENV_BIN/tunedeck-gui" "$BIN_DIR/tunedeck-gui"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=TuneDeck
GenericName=Headphone Controller
Comment=Control JBL headphones, earbuds and speakers
Exec=$BIN_DIR/tunedeck-gui
Icon=$REPO_DIR/tunedeck_gui/assets/logo.png
Terminal=false
Categories=AudioVideo;Audio;
Keywords=JBL;headphones;bluetooth;ANC;equalizer;
Actions=Simulator;

[Desktop Action Simulator]
Name=Open in Simulation Mode
Exec=$BIN_DIR/tunedeck-gui --sim
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true

echo "Installed:"
echo "  $BIN_DIR/tunedeck, $BIN_DIR/tunedeck-gui"
echo "  $DESKTOP_FILE (TuneDeck in your app menu)"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "note: $BIN_DIR is not on your PATH; add it to use the commands from any terminal." ;;
esac
