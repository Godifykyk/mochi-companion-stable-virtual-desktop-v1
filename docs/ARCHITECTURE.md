# Architecture

The repository keeps behavior data separate from desktop integrations.

- `shared/anime_modes.json` is the canonical 120-mode catalog.
- The fixed palette is white and blue on black.
- Native adapters render the catalog using their shell toolkit.
- The portable adapter uses GTK3 and optional GtkLayerShell.
- Smart-hide backends query only active-workspace/window metadata and fail open: if metadata is unavailable, Mochi remains visible.

## Adapter selection

`install.sh --adapter auto` prefers:

1. KDE Plasma widget on Plasma 6.
2. GNOME extension on GNOME 45+.
3. Noctalia when Noctalia is installed.
4. Portable GTK fallback.

## Low-power policy

Idle state changes slowly. Fast timers are used only during short animation sequences. Network access, microphones, screen capture, clipboard monitoring, and persistent databases are absent.

## Wayland limits

Normal client windows cannot choose absolute placement under Wayland. The portable adapter uses the layer-shell protocol when `GtkLayerShell` is available. GNOME Wayland does not expose the same generic placement/window-introspection capabilities, so the native GNOME extension is preferred there.
