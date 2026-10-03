#!/usr/bin/env python3
"""Portable Mochi companion for GTK3 desktops and Wayland compositors."""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]


def locate_catalog() -> pathlib.Path:
    candidates = []
    data_dir = os.environ.get("MOCHI_DATA_DIR")
    if data_dir:
        candidates.append(pathlib.Path(data_dir) / "anime_modes.json")
    candidates.extend([
        ROOT / "shared" / "anime_modes.json",
        pathlib.Path("/usr/share/mochi-companion/shared/anime_modes.json"),
        pathlib.Path.home() / ".local/share/mochi-companion/shared/anime_modes.json",
    ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("anime_modes.json was not found; set MOCHI_DATA_DIR")


CATALOG_PATH = locate_catalog()
APP_ID = "io.github.mochi.Companion"
WHITE = "#FFFFFF"
BLUE = "#53C7FF"
BLACK = "#000000"


def command_json(command: list[str]) -> Any:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1.2, check=False)
        return json.loads(result.stdout) if result.returncode == 0 and result.stdout else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def windows_hyprland() -> bool:
    workspace = command_json(["hyprctl", "-j", "activeworkspace"])
    clients = command_json(["hyprctl", "-j", "clients"])
    if not isinstance(workspace, dict) or not isinstance(clients, list):
        return False
    workspace_id = workspace.get("id")
    return any(c.get("workspace", {}).get("id") == workspace_id and APP_ID not in str(c) for c in clients)


def windows_niri() -> bool:
    workspaces = command_json(["niri", "msg", "--json", "workspaces"])
    windows = command_json(["niri", "msg", "--json", "windows"])
    if not isinstance(workspaces, list) or not isinstance(windows, list):
        return False
    active_ids = {w.get("id") for w in workspaces if w.get("is_active")}
    return any(w.get("workspace_id") in active_ids and APP_ID not in str(w) for w in windows)


def _sway_leaves(node: dict[str, Any]) -> list[dict[str, Any]]:
    children = node.get("nodes", []) + node.get("floating_nodes", [])
    if not children:
        return [node]
    leaves: list[dict[str, Any]] = []
    for child in children:
        leaves.extend(_sway_leaves(child))
    return leaves


def _sway_find_workspace(node: dict[str, Any], name: str) -> dict[str, Any] | None:
    if node.get("type") == "workspace" and node.get("name") == name:
        return node
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        found = _sway_find_workspace(child, name)
        if found is not None:
            return found
    return None


def windows_sway() -> bool:
    workspaces = command_json(["swaymsg", "-t", "get_workspaces", "-r"])
    tree = command_json(["swaymsg", "-t", "get_tree", "-r"])
    if not isinstance(workspaces, list) or not isinstance(tree, dict):
        return False
    focused = next((w.get("name") for w in workspaces if w.get("focused")), None)
    workspace_node = _sway_find_workspace(tree, focused) if focused else None
    if workspace_node is None:
        return False
    return any(
        node.get("type") == "con" and node.get("name") and APP_ID not in json.dumps(node)
        for node in _sway_leaves(workspace_node)
    )


def windows_x11() -> bool:
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=1.0, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(line.strip() and "Mochi Companion" not in line for line in result.stdout.splitlines())


def windows_kwin() -> bool:
    # Generic KWin clients lack a stable permission-free active-workspace query.
    # Fail open instead of hiding Mochi permanently from unfiltered results.
    return False


def select_window_backend():
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP", "") + ":" + os.environ.get("XDG_SESSION_DESKTOP", "")).lower()
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return windows_hyprland
    if "niri" in desktop:
        return windows_niri
    if os.environ.get("SWAYSOCK") or "sway" in desktop:
        return windows_sway
    if "kde" in desktop or "plasma" in desktop:
        return windows_kwin
    return windows_x11


def smoke_test() -> int:
    catalog = json.loads(CATALOG_PATH.read_text())
    assert len(catalog["modes"]) >= 120
    assert {frame[2] for frame in catalog["frames"].values()} <= {WHITE, BLUE}
    assert callable(select_window_backend())
    print("portable smoke test: ok")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portable Mochi desktop companion")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--no-smart-hide", action="store_true")
    parser.add_argument("--frequency", choices=("calm", "balanced", "frequent"), default="balanced")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.smoke_test:
        return smoke_test()

    import gi

    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, GLib, Gtk

    try:
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell
    except (ValueError, ImportError):
        GtkLayerShell = None

    catalog = json.loads(CATALOG_PATH.read_text())
    frames = catalog["frames"]
    modes = catalog["modes"]
    window_backend = select_window_backend()

    class MochiWindow(Gtk.Window):
        def __init__(self) -> None:
            super().__init__(title="Mochi Companion")
            self.set_name(APP_ID)
            self.set_default_size(260, 42)
            self.set_size_request(260, 42)
            self.set_decorated(False)
            self.set_resizable(False)
            self.set_keep_above(True)
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            self.set_app_paintable(True)
            screen = self.get_screen()
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)

            self.area = Gtk.DrawingArea()
            self.area.connect("draw", self.on_draw)
            self.add(self.area)
            self.connect("button-press-event", self.on_click)
            self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

            self.sequence = ["neutral"]
            self.sequence_index = 0
            self.sequence_deadline = 0.0
            self.next_moment = time.monotonic() + self.delay_seconds()
            self.hidden_for_windows = False

            if GtkLayerShell is not None and os.environ.get("WAYLAND_DISPLAY"):
                GtkLayerShell.init_for_window(self)
                GtkLayerShell.set_namespace(self, APP_ID)
                GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
                GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
                GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 8)
                GtkLayerShell.set_exclusive_zone(self, 0)
            else:
                self.connect("realize", self.position_x11)

            GLib.timeout_add(160, self.animate)
            GLib.timeout_add_seconds(2, self.smart_hide)

        def delay_seconds(self) -> int:
            if args.frequency == "frequent":
                return random.randint(6, 12)
            if args.frequency == "calm":
                return random.randint(28, 50)
            return random.randint(12, 24)

        def position_x11(self, *_args) -> None:
            geometry = self.get_screen().get_monitor_geometry(self.get_screen().get_primary_monitor())
            self.move(geometry.x + (geometry.width - 260) // 2, geometry.y + 8)

        def choose_mode(self) -> None:
            mode = random.choice(modes)
            self.sequence = list(mode.get("sequence") or ["neutral"])
            self.sequence_index = 0
            self.sequence_deadline = time.monotonic() + max(1.2, len(self.sequence) * 0.32)
            self.next_moment = self.sequence_deadline + self.delay_seconds()

        def animate(self) -> bool:
            now = time.monotonic()
            if now >= self.next_moment and len(self.sequence) == 1:
                self.choose_mode()
            if len(self.sequence) > 1:
                self.sequence_index = (self.sequence_index + 1) % len(self.sequence)
                if now >= self.sequence_deadline:
                    self.sequence = ["neutral"]
                    self.sequence_index = 0
            self.area.queue_draw()
            return True

        def smart_hide(self) -> bool:
            if args.no_smart_hide:
                return True
            occupied = window_backend()
            if occupied and not self.hidden_for_windows:
                self.set_opacity(0.0)
                self.set_sensitive(False)
                self.hidden_for_windows = True
            elif not occupied and self.hidden_for_windows:
                self.set_opacity(1.0)
                self.set_sensitive(True)
                self.hidden_for_windows = False
            return True

        def on_click(self, _widget, event) -> bool:
            if event.button == 1:
                self.sequence = ["love", "sparkle", "love", "happy"]
            elif event.button == 2:
                self.sequence = ["blink", "sleepy", "sleepy", "neutral"]
            else:
                self.sequence = ["focused", "rage", "angry", "neutral"]
            self.sequence_index = 0
            self.sequence_deadline = time.monotonic() + 1.8
            return True

        def on_draw(self, _widget, cr) -> bool:
            width, height = self.get_allocated_width(), self.get_allocated_height()
            cr.set_source_rgba(0, 0, 0, 0.98)
            radius = 14
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -math.pi / 2, 0)
            cr.arc(width - radius, height - radius, radius, 0, math.pi / 2)
            cr.arc(radius, height - radius, radius, math.pi / 2, math.pi)
            cr.arc(radius, radius, radius, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.fill()

            name = self.sequence[self.sequence_index]
            left, right, color = frames.get(name, frames["neutral"])
            rgb = (1.0, 1.0, 1.0) if color == WHITE else (0.325, 0.78, 1.0)
            cr.set_source_rgb(*rgb)
            cr.select_font_face("DejaVu Sans", 0, 1)
            cr.set_font_size(30)
            for text, cx in ((left, width * 0.32), (right, width * 0.68)):
                ext = cr.text_extents(text)
                cr.move_to(cx - ext.width / 2 - ext.x_bearing, height * 0.5 - ext.height / 2 - ext.y_bearing)
                cr.show_text(text)
            return True

    window = MochiWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
