# Mochi Eyes

A lightweight Noctalia bar widget inspired by the expressive dashboard companion style of DASEI Mochi. It contains only animated eyes: no chat box, microphone, screenshots, cloud AI, or background database.

The installed layout uses a dedicated black OLED bar at the top center of the screen, separate from the main bottom bar. The oversized eyes use Noctalia palette roles, so wallpaper-generated palettes and light/dark theme changes are applied automatically. The bar uses Noctalia smart auto-hide: it stays visible on an empty workspace and hides while that workspace contains an application window.

The original `Personal_Companion_Robot.zip` from Downloads is bundled unchanged under `references/`. Its Arduino sketch uses FluxGarage RoboEyes auto-blinking and idle movement; Mochi's local blink, look, and interaction behavior follows the same lightweight pattern without running the Arduino code on the laptop.

Mochi now has 120 original anime-inspired modes built from 20 familiar storytelling beats and six phases each. These include power surges, final stands, rival glares, comedy panic, friendship sparks, victory poses, training focus, sudden shock, secret plans, heroic arrivals, magical awakenings, speed dashes, tearful courage, festival joy, cosmic wonder, and quiet episodes. They copy no anime character or scene.

Twelve original 220×36 animated GIFs are bundled under `assets/gifs/`. Noctalia bar images are static, so Mochi plays the matching eight SVG frames at 100–220 ms intervals to produce the actual bar animation. Mochi chooses modes by himself. In balanced mode a new moment begins roughly every 12–24 seconds, with animated moments selected 20% of the time rather than continuously. Every eye and animation uses only white (`#FFFFFF`) and blue (`#53C7FF`) on the black OLED background; red and pink are excluded.

Interactions:

- Hover: surprised, then happy.
- Left click: love.
- Right click: angry.
- Middle click: sleepy.
- Scroll: look left/right.
- Focused coding/terminal apps: focused eyes.
- Music/audio peaks: happy bounce expression.

In lively mode the state timer runs every 1.5 seconds, with focused-app title/app-ID metadata checked locally about every 10 seconds. It stores and transmits none of that metadata. Rendering only changes when the expression changes, keeping the marginal idle CPU estimate below 1% of one core on this laptop.

Startup and updates:

- Niri starts Noctalia through `~/.config/niri/cfg/autostart.kdl`, so Mochi starts automatically after login or restart.
- The local source and enabled plugin are stored in Noctalia settings, while the source project remains at `/home/kanha/projects/noctalia-mochi-plugin`.
- Normal Noctalia package updates should preserve it. A future plugin-API incompatibility may require updating this local plugin, but the files are not stored inside the Noctalia package and should not be overwritten.
