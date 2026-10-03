# Compatibility

Status definitions:

- Native: integrated into the desktop panel/shell.
- Portable: GTK overlay; layer-shell on supported Wayland compositors and an always-on-top X11 fallback.
- Limited: launches, but compositor policy may control placement or smart-hide.

## Desktop and compositor matrix

| Desktop/compositor | Recommended adapter | Status | Smart hide |
|---|---|---|---|
| Hyprland | Portable GTK | Native layer-shell placement | `hyprctl` active-workspace clients |
| Niri | Noctalia or Portable GTK | Native shell plugin / layer-shell | Noctalia smart hide or `niri msg` |
| Sway | Portable GTK | Native layer-shell placement | `swaymsg` tree/workspace metadata |
| KDE Plasma 6 | Plasma widget | Native panel widget | Use Plasma panel auto-hide; portable smart-hide works on KDE X11 only |
| GNOME 45+ | GNOME extension | Native top-panel indicator | Follows GNOME panel behavior; generic Wayland overlay is limited |
| Xfce | Portable GTK | X11 overlay | `wmctrl` |
| Cinnamon | Portable GTK | X11 overlay | `wmctrl` |
| MATE | Portable GTK | X11 overlay | `wmctrl` |
| LXQt | Portable GTK | X11/KWin overlay | `wmctrl` on X11; Wayland smart-hide is unavailable |
| Budgie | Portable GTK | Usually X11 overlay | `wmctrl`; Wayland placement depends on compositor |
| COSMIC | Portable GTK | Limited fallback | Window metadata support is not guaranteed |

KDE Plasma 5 can use the portable adapter; the bundled plasmoid targets Plasma 6.

## Distribution matrix

| Distribution | Family/profile | Expected installation path |
|---|---|---|
| Arch Linux | pacman / PKGBUILD | Native dependency names included |
| Ubuntu | apt | Debian-family dependency profile |
| Debian | apt | Debian-family dependency profile |
| Fedora | dnf / RPM spec | Fedora packaging starter included |
| openSUSE | zypper | Dependency profile documented |
| Linux Mint | apt | Ubuntu/Debian profile |
| Manjaro | pacman | Arch profile |
| Pop!_OS | apt | Ubuntu profile |
| NixOS | Nix expression | Starter `default.nix` included |
| Void Linux | xbps | Dependency profile documented |

## Validation status

The release tree is tested in isolation for Python syntax, smoke-test behavior, shell syntax, JSON manifests, catalog integrity, color restrictions, installer rollback/upgrade behavior, active-workspace filtering, and file completeness. It is not claimed as runtime-verified on every desktop or distribution. Cross-desktop runtime checks belong in VMs/CI images before publishing binaries.
