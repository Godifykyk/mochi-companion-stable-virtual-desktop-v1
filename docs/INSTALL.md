# Installation

## Dependencies for the portable GTK adapter

| Distribution family | Packages |
|---|---|
| Arch Linux / Manjaro | `python python-gobject gtk3 gtk-layer-shell wmctrl` |
| Ubuntu / Debian / Linux Mint / Pop!_OS | `python3 python3-gi gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wmctrl` |
| Fedora | `python3 python3-gobject gtk3 gtk-layer-shell wmctrl` |
| openSUSE | `python3 python3-gobject-Gdk gtk3 typelib-1_0-GtkLayerShell-0_1 wmctrl` |
| Void Linux | `python3 python3-gobject gtk+3 gtk-layer-shell wmctrl` |
| NixOS | add `python3`, `python3Packages.pygobject3`, `gtk3`, `gtk-layer-shell`, and `wmctrl` to the user/system environment |

Smart-hide command helpers are optional:

- Hyprland: `hyprctl` from Hyprland.
- Niri: `niri msg` from Niri.
- Sway: `swaymsg` from Sway.
- KDE Wayland portable mode: `kdotool`; use the Plasma widget when possible.
- X11 desktops: `wmctrl`.

## Install

```text
chmod +x install.sh uninstall.sh scripts/detect-environment.sh
./install.sh --dry-run
./install.sh --adapter auto
```

Explicit adapters:

```text
./install.sh --adapter noctalia
./install.sh --adapter kde
./install.sh --adapter gnome
./install.sh --adapter portable
```

The portable adapter creates a freedesktop autostart entry unless `--no-autostart` is supplied.

## Uninstall

```text
./uninstall.sh
```

## Test without installation

These commands operate only inside this release folder:

```text
python3 -m unittest discover -s tests -v
python3 portable/mochi_companion.py --smoke-test
./install.sh --dry-run
```
