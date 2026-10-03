#!/usr/bin/env bash
set -euo pipefail

DEST="${XDG_DATA_HOME:-$HOME/.local/share}/mochi-companion"
UUID="mochi-companion@local.github.io"
STATE_FILE="$DEST/install-state"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "No Mochi Companion installation state found; nothing removed."
  exit 0
fi

adapter="$(<"$STATE_FILE")"
case "$adapter" in
  noctalia)
    if command -v noctalia >/dev/null 2>&1; then
      noctalia msg plugins disable kanha/mochi-eyes >/dev/null 2>&1 || true
      noctalia msg plugins source remove mochi-stable >/dev/null 2>&1 || true
    fi
    ;;
  kde)
    if command -v kpackagetool6 >/dev/null 2>&1; then
      kpackagetool6 --type Plasma/Applet --remove io.github.mochi.companion >/dev/null 2>&1 || true
    fi
    ;;
  gnome)
    if command -v gnome-extensions >/dev/null 2>&1; then
      gnome-extensions disable "$UUID" >/dev/null 2>&1 || true
    fi
    rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$UUID"
    ;;
  portable)
    launcher="$HOME/.local/bin/mochi-companion"
    if [[ -L "$launcher" && "$(readlink "$launcher")" == "$DEST/portable/mochi_companion.py" ]]; then
      rm -f "$launcher"
    fi
    rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/mochi-companion.desktop"
    ;;
  *)
    echo "Unknown installation state '$adapter'; refusing broad cleanup." >&2
    exit 1
    ;;
esac

rm -rf "$DEST"
echo "Mochi Companion $adapter installation removed."
