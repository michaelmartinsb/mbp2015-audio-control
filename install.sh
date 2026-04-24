#!/usr/bin/env bash
# mbp2015-audio-control installer
#
# Installs system dependencies, sets up a local Python virtual environment
# with PySide6, copies the EasyEffects presets into your user config, and
# (optionally) installs a desktop launcher.
#
# Safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
EE_INPUT_DIR="$HOME/.config/easyeffects/input"
EE_OUTPUT_DIR="$HOME/.config/easyeffects/output"
DESKTOP_TARGET="$HOME/.local/share/applications/mbp2015-audio-control.desktop"

say() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }

if [[ "$(uname -s)" != "Linux" ]]; then
  warn "This installer is intended for Linux. Detected: $(uname -s)"
fi

say "Step 1/5: install system packages (apt)"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y \
    easyeffects \
    python3 python3-venv python3-pip \
    libxcb-cursor0 libxkbcommon-x11-0 \
    libnotify-bin
else
  warn "apt-get not found. Install these manually for your distro:"
  warn "  easyeffects, python3, python3-venv, python3-pip,"
  warn "  libxcb-cursor0, libxkbcommon-x11-0, libnotify-bin"
fi

say "Step 2/5: create Python virtual environment at .venv/"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

say "Step 3/5: install EasyEffects presets"
mkdir -p "$EE_INPUT_DIR" "$EE_OUTPUT_DIR"
cp -v "$SCRIPT_DIR"/presets/input/*.json "$EE_INPUT_DIR/"
cp -v "$SCRIPT_DIR"/presets/output/*.json "$EE_OUTPUT_DIR/"

say "Step 4/5: ensure launcher is executable"
chmod +x "$SCRIPT_DIR/select-audio-profile.sh" "$SCRIPT_DIR/audio-profile-switcher.py"

say "Step 5/5: install desktop launcher (optional)"
read -r -p "Install a desktop launcher to $DESKTOP_TARGET? [Y/n] " reply
case "${reply:-Y}" in
  [Yy]*|"")
    mkdir -p "$(dirname "$DESKTOP_TARGET")"
    sed "s|__INSTALL_DIR__|$SCRIPT_DIR|g" \
      "$SCRIPT_DIR/audio-profile-switcher.desktop.template" \
      > "$DESKTOP_TARGET"
    chmod +x "$DESKTOP_TARGET"
    if command -v update-desktop-database >/dev/null 2>&1; then
      update-desktop-database "$(dirname "$DESKTOP_TARGET")" || true
    fi
    say "Installed desktop launcher: $DESKTOP_TARGET"
    ;;
  *)
    say "Skipped desktop launcher."
    ;;
esac

cat <<EOF

\033[1;32mInstall complete.\033[0m

Run the GUI:        $SCRIPT_DIR/select-audio-profile.sh
Apply via CLI:      $SCRIPT_DIR/select-audio-profile.sh --apply-output MacBook-Speakers
                    $SCRIPT_DIR/select-audio-profile.sh --apply-input  Built-in-Mic-Voice
Find the launcher:  search 'Audio Profile Switcher' in your application menu

EOF
