# Mochi Companion Stable

A GitHub-ready, eyes-only desktop companion for Linux. It ships 120 original anime-inspired moods, 12 white-and-blue GIF exports, low-power SVG/frame animation, smart workspace hiding where the desktop exposes window metadata, and native adapters for Noctalia, KDE Plasma 6, and GNOME Shell 45+.

## What is included

- `portable/` — GTK3 application for Hyprland, Niri, Sway, X11 desktops, and generic fallback use.
- `adapters/noctalia/` — Noctalia plugin copied into this isolated release tree.
- `adapters/kde-plasma-6/` — Plasma 6 panel widget.
- `adapters/gnome-shell-45-plus/` — GNOME top-panel extension.
- `shared/` — 120-mode catalog and source notes.
- `packages/` — starter packaging files for Arch, Debian/Ubuntu, Fedora, and NixOS.
- `docs/` — installation, compatibility, architecture, privacy, and packaging notes.

## Quick start

```text
./install.sh --dry-run
./install.sh --adapter auto
```

The installer is user-local and never invokes `sudo` or a package manager. Install the dependencies listed in `docs/INSTALL.md` first.

## Stable-release boundary

The Noctalia adapter is the mature implementation. The portable GTK application and native KDE/GNOME adapters are isolated release implementations validated by automated syntax, manifest, catalog, installer, and smoke tests. They were deliberately not installed or runtime-tested against the currently running Mochi instance. Runtime validation should be performed in a disposable VM or secondary user session before publishing a binary release.

## Palette and privacy

Eyes use only white (`#FFFFFF`) and blue (`#53C7FF`) on black. The project does not capture screenshots, keystrokes, clipboard contents, microphone audio, or network data. Optional smart-hide backends read only local window/workspace metadata.

See `docs/COMPATIBILITY.md` for desktop-specific limitations.
