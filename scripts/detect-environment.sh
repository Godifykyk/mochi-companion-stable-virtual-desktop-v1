#!/usr/bin/env bash
set -euo pipefail

current_desktop="${XDG_CURRENT_DESKTOP:-}:${XDG_SESSION_DESKTOP:-}"
lower="${current_desktop,,}"

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  desktop="hyprland"
elif [[ "$lower" == *niri* ]]; then
  desktop="niri"
elif [[ -n "${SWAYSOCK:-}" || "$lower" == *sway* ]]; then
  desktop="sway"
elif [[ "$lower" == *kde* || "$lower" == *plasma* ]]; then
  desktop="kde"
elif [[ "$lower" == *gnome* ]]; then
  desktop="gnome"
elif [[ "$lower" == *xfce* ]]; then
  desktop="xfce"
elif [[ "$lower" == *cinnamon* ]]; then
  desktop="cinnamon"
elif [[ "$lower" == *mate* ]]; then
  desktop="mate"
elif [[ "$lower" == *lxqt* ]]; then
  desktop="lxqt"
elif [[ "$lower" == *budgie* ]]; then
  desktop="budgie"
elif [[ "$lower" == *cosmic* ]]; then
  desktop="cosmic"
else
  desktop="generic"
fi

if command -v pacman >/dev/null 2>&1; then
  package_manager="pacman"
elif command -v apt-get >/dev/null 2>&1; then
  package_manager="apt"
elif command -v dnf >/dev/null 2>&1; then
  package_manager="dnf"
elif command -v zypper >/dev/null 2>&1; then
  package_manager="zypper"
elif command -v xbps-install >/dev/null 2>&1; then
  package_manager="xbps"
elif command -v nix-env >/dev/null 2>&1; then
  package_manager="nix"
else
  package_manager="unknown"
fi

printf 'desktop=%s\n' "$desktop"
printf 'package_manager=%s\n' "$package_manager"
printf 'session_type=%s\n' "${XDG_SESSION_TYPE:-unknown}"
