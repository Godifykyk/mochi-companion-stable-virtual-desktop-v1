#!/usr/bin/env python3
"""Generate Mochi's original anime-inspired mode catalog and GIF pack."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT / "mochi-eyes"
GIF_DIR = PLUGIN / "assets" / "gifs"
FRAME_DIR = PLUGIN / "assets" / "animation-frames"
CATALOG = PLUGIN / "anime_modes.json"

FRAMES = {
    "neutral": ["●", "●", "#FFFFFF"],
    "blink": ["━", "━", "#FFFFFF"],
    "look-left": ["◉", "●", "#53C7FF"],
    "look-right": ["●", "◉", "#53C7FF"],
    "happy": ["⌒", "⌒", "#53C7FF"],
    "love": ["♥", "♥", "#53C7FF"],
    "sleepy": ["—", "—", "#FFFFFF"],
    "angry": ["◣", "◢", "#53C7FF"],
    "sad": ["╯", "╰", "#FFFFFF"],
    "surprised": ["○", "○", "#53C7FF"],
    "wink": ["⌒", "●", "#53C7FF"],
    "focused": ["▰", "▰", "#FFFFFF"],
    "sparkle": ["✦", "✦", "#53C7FF"],
    "stars": ["★", "★", "#53C7FF"],
    "power": ["◆", "◆", "#53C7FF"],
    "rage": ["╲", "╱", "#53C7FF"],
    "dizzy": ["×", "×", "#FFFFFF"],
    "teary": ["◉", "◉", "#53C7FF"],
    "shy": ["•", "•", "#53C7FF"],
    "smirk": ["⌁", "⌁", "#FFFFFF"],
    "dash": ["◀", "▶", "#53C7FF"],
    "comedy": ["@", "@", "#53C7FF"],
    "confetti": ["✧", "✧", "#53C7FF"],
    "aura": ["◇", "◇", "#53C7FF"],
}

ARCHETYPES = [
    ("power-surge", "Power Surge", ["focused", "power", "aura", "rage"], "power-surge.gif"),
    ("final-stand", "Final Stand", ["sad", "focused", "rage", "power"], "final-stand.gif"),
    ("rival-glare", "Rival Glare", ["look-left", "smirk", "angry", "focused"], None),
    ("comedy-panic", "Comedy Panic", ["surprised", "comedy", "dizzy", "blink"], "comedy-panic.gif"),
    ("friendship-spark", "Friendship Spark", ["shy", "happy", "sparkle", "love"], "friendship-spark.gif"),
    ("victory-pose", "Victory Pose", ["focused", "happy", "stars", "confetti"], "victory-pose.gif"),
    ("training-focus", "Training Focus", ["blink", "focused", "dash", "power"], None),
    ("sudden-shock", "Sudden Shock", ["neutral", "surprised", "comedy", "dizzy"], "sudden-shock.gif"),
    ("secret-plan", "Secret Plan", ["look-left", "look-right", "smirk", "wink"], None),
    ("heroic-arrival", "Heroic Arrival", ["dash", "focused", "power", "happy"], None),
    ("magical-awakening", "Magical Awakening", ["sleepy", "sparkle", "aura", "stars"], "magical-awakening.gif"),
    ("speed-dash", "Speed Dash", ["look-left", "dash", "focused", "look-right"], "speed-dash.gif"),
    ("tearful-courage", "Tearful Courage", ["sad", "teary", "focused", "happy"], "tearful-courage.gif"),
    ("villain-smirk", "Villain Smirk", ["look-right", "smirk", "angry", "wink"], None),
    ("festival-joy", "Festival Joy", ["happy", "confetti", "stars", "love"], "festival-joy.gif"),
    ("snack-bliss", "Snack Bliss", ["surprised", "happy", "sleepy", "love"], None),
    ("rain-melancholy", "Rain Melancholy", ["neutral", "sad", "teary", "sleepy"], "rain-melancholy.gif"),
    ("cosmic-wonder", "Cosmic Wonder", ["surprised", "sparkle", "stars", "aura"], "cosmic-wonder.gif"),
    ("determined-comeback", "Determined Comeback", ["sad", "blink", "focused", "power"], None),
    ("sleepy-episode", "Sleepy Episode", ["neutral", "blink", "sleepy", "sleepy"], None),
]

PHASES = [
    ("opening", "Opening", "neutral"),
    ("build-up", "Build-up", "focused"),
    ("climax", "Climax", "power"),
    ("reaction", "Reaction", "surprised"),
    ("calm-after", "Calm After", "sleepy"),
    ("encore", "Encore", "sparkle"),
]

GIF_THEMES = {slug: (sequence, gif_name) for slug, _, sequence, gif_name in ARCHETYPES if gif_name}


def star_points(cx: float, cy: float, outer: float, inner: float, points: int = 5) -> str:
    coords = []
    for i in range(points * 2):
        angle = -math.pi / 2 + i * math.pi / points
        radius = outer if i % 2 == 0 else inner
        coords.append(f"{cx + math.cos(angle) * radius:.2f},{cy + math.sin(angle) * radius:.2f}")
    return " ".join(coords)


def eye_shape(kind: str, cx: int, side: int, accent: str) -> str:
    white = "#FFFFFF"
    if kind == "blink" or kind == "sleepy":
        return f'<path d="M {cx-16} 19 Q {cx} {14 if kind == "sleepy" else 18} {cx+16} 19" fill="none" stroke="{white}" stroke-width="5" stroke-linecap="round"/>'
    if kind == "happy":
        return f'<path d="M {cx-16} 23 Q {cx} 7 {cx+16} 23" fill="none" stroke="{white}" stroke-width="5" stroke-linecap="round"/>'
    if kind == "sad" or kind == "teary":
        drop = f'<path d="M {cx+side*8} 26 Q {cx+side*13} 31 {cx+side*8} 34 Q {cx+side*3} 31 {cx+side*8} 26" fill="#53C7FF"/>' if kind == "teary" else ""
        return f'<path d="M {cx-15} 12 Q {cx} 27 {cx+15} 12" fill="none" stroke="{white}" stroke-width="5" stroke-linecap="round"/>{drop}'
    if kind == "love":
        return f'<path d="M {cx} 29 C {cx-27} 13 {cx-13} 1 {cx} 11 C {cx+13} 1 {cx+27} 13 {cx} 29 Z" fill="#53C7FF"/>'
    if kind in ("stars", "sparkle", "confetti"):
        points = star_points(cx, 18, 15, 6, 5 if kind == "stars" else 4)
        return f'<polygon points="{points}" fill="{accent}"/>'
    if kind in ("angry", "rage"):
        pts = f"{cx-18},11 {cx+18},5 {cx+13},28 {cx-13},28"
        if side > 0:
            pts = f"{cx-18},5 {cx+18},11 {cx+13},28 {cx-13},28"
        return f'<polygon points="{pts}" fill="#53C7FF"/>'
    if kind in ("power", "aura"):
        return f'<polygon points="{cx},3 {cx+17},18 {cx},33 {cx-17},18" fill="{accent}"/>'
    if kind == "surprised":
        return f'<circle cx="{cx}" cy="18" r="13" fill="none" stroke="{white}" stroke-width="5"/>'
    if kind in ("dizzy", "comedy"):
        return f'<path d="M {cx-12} 7 L {cx+12} 29 M {cx+12} 7 L {cx-12} 29" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>'
    if kind == "dash":
        return f'<polygon points="{cx-20},9 {cx+18},5 {cx+10},27 {cx-22},30" fill="{accent}"/>'
    if kind == "smirk":
        return f'<path d="M {cx-16} {22-side*2} Q {cx} {13+side*2} {cx+16} {18+side*2}" fill="none" stroke="{white}" stroke-width="5" stroke-linecap="round"/>'
    if kind == "shy":
        return f'<ellipse cx="{cx}" cy="18" rx="7" ry="11" fill="{white}"/><ellipse cx="{cx+side*22}" cy="27" rx="7" ry="3" fill="#53C7FF" opacity=".65"/>'
    if kind == "wink" and side < 0:
        return f'<path d="M {cx-15} 21 Q {cx} 10 {cx+15} 21" fill="none" stroke="{white}" stroke-width="5" stroke-linecap="round"/>'
    if kind == "focused":
        return f'<rect x="{cx-17}" y="9" width="34" height="18" rx="4" fill="{white}"/>'
    if kind == "look-left":
        return f'<ellipse cx="{cx-6}" cy="18" rx="12" ry="15" fill="{white}"/>'
    if kind == "look-right":
        return f'<ellipse cx="{cx+6}" cy="18" rx="12" ry="15" fill="{white}"/>'
    return f'<ellipse cx="{cx}" cy="18" rx="13" ry="16" fill="{white}"/>'


def make_svg(kind: str, pulse: int) -> str:
    accent_cycle = ["#53C7FF", "#FFFFFF", "#53C7FF", "#FFFFFF"]
    accent = accent_cycle[pulse % len(accent_cycle)]
    scale = 1.0 + (0.06 if pulse % 4 in (1, 2) else 0.0)
    left = eye_shape(kind, 67, -1, accent)
    right = eye_shape(kind, 153, 1, accent)
    aura = ""
    if pulse % 2 == 1:
        aura = f'<path d="M 16 18 L 30 13 M 190 13 L 204 18 M 18 28 L 34 25 M 186 25 L 202 28" stroke="{accent}" stroke-width="3" stroke-linecap="round" opacity=".8"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="220" height="36" viewBox="0 0 220 36">
<rect width="220" height="36" rx="12" fill="#000000"/>
<g transform="translate(110 18) scale({scale}) translate(-110 -18)">{left}{right}</g>{aura}
</svg>'''


def build_catalog() -> dict:
    modes = []
    for archetype_slug, archetype_title, base_sequence, gif_name in ARCHETYPES:
        for phase_index, (phase_slug, phase_title, phase_frame) in enumerate(PHASES):
            rotated = base_sequence[phase_index % len(base_sequence):] + base_sequence[:phase_index % len(base_sequence)]
            sequence = [rotated[0], phase_frame, rotated[1], rotated[2], rotated[3]]
            mode = {
                "id": f"{archetype_slug}-{phase_slug}",
                "title": f"{archetype_title} — {phase_title}",
                "sequence": sequence,
            }
            if gif_name and phase_slug == "climax":
                mode["gif"] = f"assets/gifs/{gif_name}"
                stem = Path(gif_name).stem
                mode["animation_frames"] = [
                    f"assets/animation-frames/{stem}/{index:02d}.svg" for index in range(8)
                ]
            modes.append(mode)
    return {"frames": FRAMES, "modes": modes}


def build_gifs() -> None:
    GIF_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(FRAME_DIR, ignore_errors=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for slug, (sequence, gif_name) in GIF_THEMES.items():
        frame_paths = []
        mode_dir = FRAME_DIR / slug
        mode_dir.mkdir(parents=True, exist_ok=True)
        expanded = [sequence[0], sequence[1], sequence[2], sequence[3], sequence[2], sequence[1], "blink", sequence[0]]
        for index, frame_name in enumerate(expanded):
            frame_path = mode_dir / f"{index:02d}.svg"
            frame_path.write_text(make_svg(frame_name, index))
            frame_paths.append(frame_path)
        output = GIF_DIR / gif_name
        command = ["magick", "-background", "black", "-delay", "12", "-loop", "0"]
        command.extend(str(path) for path in frame_paths)
        command.extend(["-layers", "Optimize", str(output)])
        subprocess.run(command, check=True)


def main() -> None:
    CATALOG.write_text(json.dumps(build_catalog(), indent=2, ensure_ascii=False) + "\n")
    build_gifs()
    print(f"generated {CATALOG}")
    print(f"generated {len(GIF_THEMES)} GIFs in {GIF_DIR}")


if __name__ == "__main__":
    main()
