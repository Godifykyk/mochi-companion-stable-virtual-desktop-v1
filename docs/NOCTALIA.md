# Noctalia adapter

The Noctalia source lives at `adapters/noctalia/` and is independent of any currently installed local source.

Install from this release tree:

```text
noctalia msg plugins source add mochi-stable path /absolute/path/to/mochi-companion-stable-v1/adapters/noctalia
noctalia msg plugins enable kanha/mochi-eyes
```

Then add a widget instance of type `kanha/mochi-eyes:eyes` and place it in a dedicated bar. Suggested options:

```text
[bar.mochi]
position = "top"
thickness = 38
background_opacity = 1.0
color = "#000000"
smart_auto_hide = true
show_on_workspace_switch = false
reserve_space = false
center = ["mochi"]

[widget.mochi]
type = "kanha/mochi-eyes:eyes"
anime_moments = true
gif_moments = true
moment_frequency = "balanced"
```

Noctalia updates normally preserve local sources stored outside the package directory, but a future plugin API change may require an adapter update.
