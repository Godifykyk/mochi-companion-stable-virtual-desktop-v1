#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/mochi-companion"
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
STATE_FILE="$DEST/install-state"
ADAPTER="auto"
DRY_RUN=false
ENABLE_AUTOSTART=true

usage() {
  cat <<'EOF'
Usage: ./install.sh [--adapter auto|portable|noctalia|kde|gnome] [--dry-run] [--no-autostart]

Installs only into the current user's home directory. It never invokes sudo or a package manager.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --adapter)
      [[ $# -ge 2 ]] || { echo "--adapter requires a value" >&2; exit 2; }
      ADAPTER="$2"
      shift 2
      ;;
    --dry-run) DRY_RUN=true; shift ;;
    --no-autostart) ENABLE_AUTOSTART=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$ADAPTER" in
  auto|portable|noctalia|kde|gnome) ;;
  *) echo "Unsupported adapter: $ADAPTER" >&2; exit 2 ;;
esac

run() {
  if $DRY_RUN; then
    printf 'DRY-RUN:'; printf ' %q' "$@"; printf '\n'
  else
    "$@"
  fi
}

gnome_version_supported() {
  command -v gnome-shell >/dev/null 2>&1 || return 1
  local version major
  version="$(gnome-shell --version 2>/dev/null)" || return 1
  [[ "$version" =~ ([0-9]+)(\.[0-9]+)? ]] || return 1
  major="${BASH_REMATCH[1]}"
  (( major >= 45 && major <= 51 ))
}

mapfile -t detected < <("$ROOT/scripts/detect-environment.sh")
desktop="generic"
for line in "${detected[@]}"; do
  [[ "$line" == desktop=* ]] && desktop="${line#desktop=}"
done

if [[ "$ADAPTER" == auto ]]; then
  if [[ "$desktop" == kde ]] && command -v kpackagetool6 >/dev/null 2>&1; then
    ADAPTER="kde"
  elif [[ "$desktop" == gnome ]]; then
    if command -v gnome-extensions >/dev/null 2>&1 && gnome_version_supported; then
      ADAPTER="gnome"
    else
      ADAPTER="portable"
    fi
  elif command -v noctalia >/dev/null 2>&1; then
    ADAPTER="noctalia"
  else
    ADAPTER="portable"
  fi
fi

case "$ADAPTER" in
  noctalia)
    command -v noctalia >/dev/null 2>&1 || { echo "Noctalia is required for this adapter." >&2; exit 1; }
    ;;
  kde)
    command -v kpackagetool6 >/dev/null 2>&1 || { echo "Plasma 6 kpackagetool6 is required." >&2; exit 1; }
    ;;
  gnome)
    command -v gnome-extensions >/dev/null 2>&1 || { echo "gnome-extensions is required." >&2; exit 1; }
    gnome_version_supported || { echo "GNOME Shell 45 through 51 is required." >&2; exit 1; }
    ;;
esac

if [[ -f "$STATE_FILE" ]]; then
  previous_adapter="$(<"$STATE_FILE")"
  if [[ "$previous_adapter" != "$ADAPTER" ]]; then
    echo "Adapter '$previous_adapter' is already installed; run ./uninstall.sh before switching." >&2
    exit 1
  fi
fi

run mkdir -p "$DEST" "$BIN_DIR" "$AUTOSTART_DIR"
run cp -a "$ROOT/shared" "$ROOT/portable" "$ROOT/adapters" "$DEST/"

case "$ADAPTER" in
  noctalia)
    run noctalia msg plugins source add mochi-stable path "$DEST/adapters/noctalia"
    run noctalia msg plugins enable kanha/mochi-eyes
    echo "Install the widget in a Noctalia bar through Settings, or use docs/NOCTALIA.md."
    ;;
  kde)
    run kpackagetool6 --type Plasma/Applet --install "$DEST/adapters/kde-plasma-6/package"
    echo "Add 'Mochi Companion' to a Plasma panel. Plasma controls panel auto-hide."
    ;;
  gnome)
    uuid="mochi-companion@local.github.io"
    extension_dir="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$uuid"
    run mkdir -p "$(dirname "$extension_dir")"
    run rm -rf "$extension_dir"
    run mkdir -p "$extension_dir"
    run cp -a "$DEST/adapters/gnome-shell-45-plus/." "$extension_dir/"
    if ! $DRY_RUN; then
      gnome-extensions enable "$uuid" || echo "Log out/in, then enable $uuid with Extension Manager."
    fi
    ;;
  portable)
    run ln -sfn "$DEST/portable/mochi_companion.py" "$BIN_DIR/mochi-companion"
    run chmod +x "$DEST/portable/mochi_companion.py"
    if $ENABLE_AUTOSTART; then
      if $DRY_RUN; then
        echo "DRY-RUN: create $AUTOSTART_DIR/mochi-companion.desktop"
      else
        cat > "$AUTOSTART_DIR/mochi-companion.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Mochi Companion
Comment=White-and-blue animated robot eyes
Exec="$BIN_DIR/mochi-companion"
Icon=face-smile
Terminal=false
X-GNOME-Autostart-enabled=true
Categories=Utility;
EOF
      fi
    fi
    ;;
esac

if $DRY_RUN; then
  echo "DRY-RUN: write adapter state to $STATE_FILE"
else
  printf '%s\n' "$ADAPTER" > "$STATE_FILE"
fi

echo "Installed adapter: $ADAPTER"
echo "Files: $DEST"
