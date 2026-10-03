# Mochi Eyes

A lightweight, eyes-only Noctalia bar widget inspired by expressive dashboard companions. It does not use chat, microphones, screenshots, cloud AI, or a background database.

The widget renders on a fixed black surface with white (`#FFFFFF`) and blue (`#53C7FF`) eyes. It includes 120 original anime-inspired modes and twelve GIF exports; Noctalia playback uses the bundled SVG animation frames.

Interactions:

- Hover: surprised, then happy.
- Left click: love.
- Right click: angry.
- Middle click: sleepy.
- Scroll: look left/right.
- Focused coding or terminal apps on Niri: focused eyes.
- Optional audio spectrum events: happy expression.

Activity awareness reads only the focused window title and app ID through `niri msg` about every ten seconds. The metadata is processed locally and is not stored or transmitted.

Install the widget through the release-level `install.sh --adapter noctalia` command, then add “Mochi Eyes” to a Noctalia bar. Bar placement and auto-hide behavior are controlled by the user’s Noctalia configuration.

This release targets Noctalia plugin API 32. Future Noctalia API changes may require an adapter update.
