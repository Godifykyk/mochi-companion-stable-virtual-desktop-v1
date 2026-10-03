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
cleanup_failed=false
noctalia_target_enabled() {
  local plugin_list="$1"
  local line
  while IFS= read -r line; do
    if [[ "$line" == "kanha/mochi-eyes [mochi-stable] "* && "$line" == *" enabled" ]]; then
      return 0
    fi
  done <<< "$plugin_list"
  return 1
}
case "$adapter" in
  noctalia)
    if ! command -v noctalia >/dev/null 2>&1; then
      cleanup_failed=true
    else
      plugin_list="$(noctalia msg plugins list 2>/dev/null)" || cleanup_failed=true
      source_list="$(noctalia msg plugins source list 2>/dev/null)" || cleanup_failed=true
      if noctalia_target_enabled "$plugin_list"; then
        noctalia msg plugins disable kanha/mochi-eyes >/dev/null 2>&1 || cleanup_failed=true
      fi
      if [[ "$source_list" == *"mochi-stable "* ]]; then
        noctalia msg plugins source remove mochi-stable >/dev/null 2>&1 || cleanup_failed=true
      fi
    fi
    ;;
  kde)
    if ! command -v kpackagetool6 >/dev/null 2>&1; then
      cleanup_failed=true
    else
      package_list="$(kpackagetool6 --type Plasma/Applet --list 2>/dev/null)" || cleanup_failed=true
      if [[ "$package_list" == *"io.github.mochi.companion"* ]]; then
        kpackagetool6 --type Plasma/Applet --remove io.github.mochi.companion >/dev/null 2>&1 || cleanup_failed=true
      fi
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
    autostart="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/mochi-companion.desktop"
    if [[ -f "$autostart" ]] && grep -qx 'X-Mochi-Companion-Managed=true' "$autostart"; then
      rm -f "$autostart"
    fi
    ;;
  *)
    echo "Unknown installation state '$adapter'; refusing broad cleanup." >&2
    exit 1
    ;;
esac

if $cleanup_failed; then
  echo "Native $adapter cleanup failed; installation state was retained for retry." >&2
  exit 1
fi

rm -rf "$DEST"
echo "Mochi Companion $adapter installation removed."
