# Mochi Companion Stable

An eyes-only Linux desktop companion with 120 original anime-inspired moods, twelve white-and-blue GIF exports, low-power SVG/frame animation, and native adapters for Noctalia, KDE Plasma 6, and GNOME Shell 45+. A portable GTK3/layer-shell application is included for Niri, Hyprland, Sway, X11 desktops, and generic fallback use.

## Mochi preview

![Mochi Companion showing its happy expression](docs/images/mochi-preview.png)

## Features

- 120 original animated moods and expression sequences.
- Fixed white (`#FFFFFF`) and blue (`#53C7FF`) palette on black.
- Noctalia plugin API 32 adapter.
- KDE Plasma 6 panel widget.
- GNOME Shell 45–51 top-panel extension.
- Portable GTK3 application with Niri, Hyprland, Sway, KWin/X11, and `wmctrl` awareness backends.
- Smart workspace hiding where the desktop exposes suitable window metadata.
- User-local transactional installer with rollback and ownership checks.
- No screenshots, keystroke capture, clipboard access, microphone recording, cloud AI, or telemetry.

## Repository layout

- `portable/` — portable GTK3/layer-shell application.
- `adapters/noctalia/` — Noctalia bar widget.
- `adapters/kde-plasma-6/` — Plasma 6 panel widget.
- `adapters/gnome-shell-45-plus/` — GNOME top-panel extension.
- `shared/` — shared 120-mode catalog.
- `packages/` — Arch, Debian/Ubuntu, Fedora, and Nix packaging files.
- `docs/` — installation, compatibility, architecture, privacy, Noctalia, and packaging documentation.
- `tests/` — automated release and installer safety tests.

## Download

Verified v1.0.0 archives and checksums are stored in `release-assets/v1.0.0/`:

- `mochi-companion-stable-v1.0.0.zip`
- `mochi-companion-stable-v1.0.0.tar.gz`
- `SHA256SUMS`

Download the ZIP or tarball, then extract it:

```bash
unzip mochi-companion-stable-v1.0.0.zip
cd mochi-companion-stable-v1
```

Or clone the repository:

```bash
git clone https://github.com/Godifykyk/mochi-companion-stable-virtual-desktop-v1.git
cd mochi-companion-stable-virtual-desktop-v1
```

## Dependencies

The exact package names vary by distribution. The portable application needs:

- Python 3
- PyGObject / `python3-gi`
- GTK 3
- GTK Layer Shell bindings when running as a Wayland layer-shell surface

Optional smart-hide helpers:

- Niri: `niri msg`
- Hyprland: `hyprctl`
- Sway: `swaymsg`
- X11 desktops and KDE X11: `wmctrl`

Native adapters additionally need their target desktop: Noctalia, KDE Plasma 6, or GNOME Shell 45–51. See `docs/INSTALL.md` and `docs/COMPATIBILITY.md` for details.

## Preview the installation

The installer is user-local. It never invokes `sudo` or a package manager.

```bash
./install.sh --dry-run
```

Preview a specific adapter:

```bash
./install.sh --adapter portable --dry-run
./install.sh --adapter noctalia --dry-run
./install.sh --adapter kde --dry-run
./install.sh --adapter gnome --dry-run
```

## Install automatically

The automatic mode detects the available desktop integration and falls back to the portable application:

```bash
./install.sh --adapter auto
```

## Install a specific adapter

Portable GTK application:

```bash
./install.sh --adapter portable
```

Portable application without a login autostart entry:

```bash
./install.sh --adapter portable --no-autostart
```

Noctalia widget:

```bash
./install.sh --adapter noctalia
```

After installation, add “Mochi Eyes” to a Noctalia bar through Noctalia Settings.

KDE Plasma 6 widget:

```bash
./install.sh --adapter kde
```

After installation, add “Mochi Companion” to a Plasma panel.

GNOME Shell 45–51 extension:

```bash
./install.sh --adapter gnome
```

If GNOME cannot enable it immediately, log out and back in, then enable `mochi-companion@local.github.io` with Extension Manager or `gnome-extensions`.

## Reinstall or update

Run the same installation command again. The installer stages the new payload, replaces it transactionally, and restores the previous payload if installation fails.

```bash
./install.sh --adapter portable
```

Switching between adapters requires uninstalling the currently recorded adapter first.

## Uninstall

```bash
./uninstall.sh
```

The uninstaller removes only the recorded Mochi adapter and files it owns. If native desktop cleanup cannot complete, it retains installation state so cleanup can be retried.

## Run the portable application from source

```bash
python portable/mochi_companion.py
```

Run its non-GUI smoke test:

```bash
python portable/mochi_companion.py --smoke-test
```

## Test the release

```bash
python -m unittest discover -s tests -v
bash -n install.sh uninstall.sh scripts/*.sh
python -m py_compile portable/mochi_companion.py
```

The verified v1.0.0 release passes 47 automated tests and the portable smoke test. Both published archive formats were extracted and tested independently.

## Compatibility status

The existing Noctalia/Niri implementation is the mature, live-tested adapter. Portable and native KDE/GNOME implementations are covered by automated behavior, syntax, manifest, packaging, installer, rollback, and environment-profile tests. They are not claimed as runtime-tested on every listed desktop or Linux distribution.

See `docs/COMPATIBILITY.md` for the complete matrix and limitations.

## Privacy

Mochi does not capture screenshots, keystrokes, clipboard contents, microphone audio, or network data. Optional activity awareness reads only local window/workspace metadata through the desktop compositor and does not store or transmit it.

## License

MIT — see `LICENSE`.
