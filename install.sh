#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/mochi-companion"
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/mochi-companion.desktop"
LAUNCHER="$BIN_DIR/mochi-companion"
STATE_FILE="$DEST/install-state"
ADAPTER="auto"
DRY_RUN=false
ENABLE_AUTOSTART=true
REINSTALL=false

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

if [[ -L "$DEST" ]]; then
  echo "Refusing symlinked installation destination: $DEST" >&2
  exit 1
fi
if [[ -e "$DEST" && ! -d "$DEST" ]]; then
  echo "Refusing non-directory installation destination: $DEST" >&2
  exit 1
fi
if [[ -d "$DEST" && ! -f "$STATE_FILE" ]]; then
  echo "Refusing unowned installation destination: $DEST" >&2
  exit 1
fi

if [[ -f "$STATE_FILE" ]]; then
  previous_adapter="$(<"$STATE_FILE")"
  if [[ "$previous_adapter" != "$ADAPTER" ]]; then
    echo "Adapter '$previous_adapter' is already installed; run ./uninstall.sh before switching." >&2
    exit 1
  fi
  REINSTALL=true
fi

autostart_owned() {
  [[ -f "$AUTOSTART_FILE" ]] && grep -qx 'X-Mochi-Companion-Managed=true' "$AUTOSTART_FILE"
}

launcher_owned() {
  [[ -L "$LAUNCHER" ]] && [[ "$(readlink "$LAUNCHER")" == "$DEST/portable/mochi_companion.py" ]]
}

if [[ "$ADAPTER" == portable && -e "$AUTOSTART_FILE" ]] && ! autostart_owned; then
  echo "Refusing to overwrite unowned autostart file: $AUTOSTART_FILE" >&2
  exit 1
fi
if [[ "$ADAPTER" == portable && ( -e "$LAUNCHER" || -L "$LAUNCHER" ) ]] && ! launcher_owned; then
  echo "Refusing to replace unowned launcher: $LAUNCHER" >&2
  exit 1
fi

transaction_active=false
payload_switched=false
stage=""
backup=""
noctalia_source_added=false
noctalia_source_updated=false
kde_package_changed=false
gnome_extension_changed=false
extension_dir=""
extension_backup=""
portable_launcher_created=false
autostart_changed=false
autostart_backup=""
rollback_payload() {
  local status=$?
  local rollback_failed=false
  if $transaction_active; then
    set +e
    if [[ -n "$stage" ]] && ! rm -rf "$stage"; then
      rollback_failed=true
    fi

    if $REINSTALL && $payload_switched; then
      chmod -R u+rwX "$DEST" >/dev/null 2>&1
      if ! rm -rf "$DEST" || [[ -z "$backup" ]] || ! mv "$backup" "$DEST"; then
        rollback_failed=true
      else
        backup=""
      fi
    fi

    if $noctalia_source_added; then
      noctalia msg plugins disable kanha/mochi-eyes >/dev/null 2>&1 || true
      if ! noctalia msg plugins source remove mochi-stable >/dev/null 2>&1; then
        rollback_failed=true
      fi
    elif $noctalia_source_updated; then
      if ! noctalia msg plugins update mochi-stable >/dev/null 2>&1; then
        rollback_failed=true
      fi
    fi
    if $kde_package_changed; then
      if $REINSTALL; then
        if ! kpackagetool6 --type Plasma/Applet --upgrade "$DEST/adapters/kde-plasma-6/package" >/dev/null 2>&1; then
          rollback_failed=true
        fi
      elif ! kpackagetool6 --type Plasma/Applet --remove io.github.mochi.companion >/dev/null 2>&1; then
        rollback_failed=true
      fi
    fi
    if $gnome_extension_changed; then
      if ! rm -rf "$extension_dir"; then
        rollback_failed=true
      fi
      if [[ -n "$extension_backup" ]] && ! mv "$extension_backup" "$extension_dir"; then
        rollback_failed=true
      fi
    fi
    if $portable_launcher_created && ! rm -f "$LAUNCHER"; then
      rollback_failed=true
    fi
    if $autostart_changed; then
      if ! rm -f "$AUTOSTART_FILE"; then
        rollback_failed=true
      fi
      if [[ -n "$autostart_backup" ]] && ! mv "$autostart_backup" "$AUTOSTART_FILE"; then
        rollback_failed=true
      fi
    fi

    if ! $REINSTALL && $payload_switched; then
      if $rollback_failed; then
        chmod u+w "$DEST" >/dev/null 2>&1 || true
        printf '%s\n' "$ADAPTER" > "$STATE_FILE" 2>/dev/null || true
      else
        chmod -R u+rwX "$DEST" >/dev/null 2>&1
        if ! rm -rf "$DEST"; then
          rollback_failed=true
          chmod u+w "$DEST" >/dev/null 2>&1 || true
          printf '%s\n' "$ADAPTER" > "$STATE_FILE" 2>/dev/null || true
        fi
      fi
    fi

    if $rollback_failed; then
      echo "Rollback incomplete; installation payload/state was retained for cleanup retry." >&2
      [[ -z "$backup" ]] || echo "Previous payload backup retained at: $backup" >&2
    fi
  fi
  (( status != 0 )) || status=1
  exit "$status"
}

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

verify_noctalia_enabled() {
  $DRY_RUN && return 0
  local attempts="${MOCHI_NOCTALIA_VERIFY_ATTEMPTS:-20}"
  local delay="${MOCHI_NOCTALIA_VERIFY_DELAY:-0.25}"
  local plugin_list
  for (( attempt = 0; attempt < attempts; attempt++ )); do
    plugin_list="$(noctalia msg plugins list 2>/dev/null)" || plugin_list=""
    if noctalia_target_enabled "$plugin_list"; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

if $DRY_RUN; then
  run mkdir -p "$(dirname "$DEST")" "$BIN_DIR" "$AUTOSTART_DIR"
  echo "DRY-RUN: stage shared, portable, and adapters payload beside $DEST"
  echo "DRY-RUN: atomically replace $DEST after staging succeeds"
else
  dest_parent="$(dirname "$DEST")"
  mkdir -p "$dest_parent" "$BIN_DIR" "$AUTOSTART_DIR"
  stage="$(mktemp -d "$dest_parent/.mochi-companion.stage.XXXXXX")"
  transaction_active=true
  trap rollback_payload EXIT
  cp -a "$ROOT/shared" "$ROOT/portable" "$ROOT/adapters" "$stage/"
  if [[ -d "$DEST" ]]; then
    backup="$(mktemp -d "$dest_parent/.mochi-companion.backup.XXXXXX")"
    rmdir "$backup"
    mv "$DEST" "$backup"
  fi
  mv "$stage" "$DEST"
  stage=""
  payload_switched=true
fi

case "$ADAPTER" in
  noctalia)
    if $REINSTALL; then
      $DRY_RUN || noctalia_source_updated=true
      if ! run noctalia msg plugins update mochi-stable; then
        echo "Failed to update the existing Noctalia source." >&2
        exit 1
      fi
    else
      if ! run noctalia msg plugins source add mochi-stable path "$DEST/adapters/noctalia"; then
        echo "Failed to register the Noctalia source." >&2
        exit 1
      fi
      $DRY_RUN || noctalia_source_added=true
    fi
    if ! run noctalia msg plugins enable kanha/mochi-eyes; then
      echo "Failed to enable Mochi." >&2
      exit 1
    fi
    if ! verify_noctalia_enabled; then
      echo "Noctalia did not confirm that Mochi was enabled." >&2
      exit 1
    fi
    echo "Install the widget in a Noctalia bar through Settings, or use docs/NOCTALIA.md."
    ;;
  kde)
    if $REINSTALL; then
      run kpackagetool6 --type Plasma/Applet --upgrade "$DEST/adapters/kde-plasma-6/package"
    else
      run kpackagetool6 --type Plasma/Applet --install "$DEST/adapters/kde-plasma-6/package"
    fi
    $DRY_RUN || kde_package_changed=true
    echo "Add 'Mochi Companion' to a Plasma panel. Plasma controls panel auto-hide."
    ;;
  gnome)
    uuid="mochi-companion@local.github.io"
    extension_dir="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$uuid"
    run mkdir -p "$(dirname "$extension_dir")"
    if ! $DRY_RUN && [[ -d "$extension_dir" ]]; then
      extension_backup="$(mktemp -d "$(dirname "$extension_dir")/.mochi-extension.backup.XXXXXX")"
      rmdir "$extension_backup"
      mv "$extension_dir" "$extension_backup"
    else
      run rm -rf "$extension_dir"
    fi
    $DRY_RUN || gnome_extension_changed=true
    run mkdir -p "$extension_dir"
    run cp -a "$DEST/adapters/gnome-shell-45-plus/." "$extension_dir/"
    if ! $DRY_RUN; then
      gnome-extensions enable "$uuid" || echo "Log out/in, then enable $uuid with Extension Manager."
    fi
    ;;
  portable)
    if [[ ! -L "$LAUNCHER" ]]; then
      portable_launcher_created=true
    fi
    run ln -sfn "$DEST/portable/mochi_companion.py" "$LAUNCHER"
    run chmod +x "$DEST/portable/mochi_companion.py"
    if $ENABLE_AUTOSTART; then
      if $DRY_RUN; then
        echo "DRY-RUN: create $AUTOSTART_FILE"
      else
        if [[ -f "$AUTOSTART_FILE" ]]; then
          autostart_backup="$(mktemp "$AUTOSTART_DIR/.mochi-autostart.backup.XXXXXX")"
          cp -a "$AUTOSTART_FILE" "$autostart_backup"
        fi
        autostart_changed=true
        cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Mochi Companion
Comment=White-and-blue animated robot eyes
Exec="$BIN_DIR/mochi-companion"
Icon=face-smile
Terminal=false
X-GNOME-Autostart-enabled=true
X-Mochi-Companion-Managed=true
Categories=Utility;
EOF
      fi
    elif autostart_owned; then
      if ! $DRY_RUN; then
        autostart_backup="$(mktemp "$AUTOSTART_DIR/.mochi-autostart.backup.XXXXXX")"
        cp -a "$AUTOSTART_FILE" "$autostart_backup"
        autostart_changed=true
      fi
      run rm -f "$AUTOSTART_FILE"
    fi
    ;;
esac

if $DRY_RUN; then
  echo "DRY-RUN: write adapter state to $STATE_FILE"
else
  printf '%s\n' "$ADAPTER" > "$STATE_FILE"
  transaction_active=false
  trap - EXIT
  [[ -z "$backup" ]] || rm -rf "$backup"
  [[ -z "$extension_backup" ]] || rm -rf "$extension_backup"
  [[ -z "$autostart_backup" ]] || rm -f "$autostart_backup"
fi

echo "Installed adapter: $ADAPTER"
echo "Files: $DEST"
