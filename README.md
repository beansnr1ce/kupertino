# kupertino

**macOS behavior for KDE Plasma — keyd layers, KWin scripts, and muscle-memory parity.**

Not a theme. kupertino doesn't try to make Linux *look* like macOS — it makes it *behave* like macOS everywhere muscle memory matters: ⌘C/⌘V with Command next to the spacebar, ⌘Tab app switching, ⌘Space launcher, ⌥-word / ⌘-line text navigation, ⇧⌘4 screenshots, Control-arrow Spaces, and all 22 of [Rectangle.app](https://github.com/rxhanson/rectangle)'s window-management shortcuts.

Built and daily-driven on **CachyOS + KDE Plasma 6 (Wayland)**. Everything here is extracted from a working machine; a configurable installer is the roadmap, not yet reality — for now this repo is the reference implementation plus the docs to apply it by hand.

## How it works

One idea, applied consistently: **remap once, at the lowest level, and let everything above adapt.**

[keyd](https://github.com/rvaiya/keyd) rewrites modifiers at the kernel-input level so the physical modifier row mirrors a Mac's — Control, Option, Command reading toward the spacebar:

| You physically press | Apps/KDE see | macOS role |
|---|---|---|
| Ctrl (corner) | **Meta** | ⌃ Control — window management, Spaces |
| Super/Win | **Alt** | ⌥ Option — word-wise movement |
| Alt (next to space) | **Ctrl** | ⌘ Command — shortcuts |

Everything else — launcher bindings, KWin shortcuts, the Rectangle script — is configured in *post-remap* terms on top of that foundation. keyd layers (not plain swaps) add the macOS text-editing behaviors: ⌘←/→ line jumps, ⌥←/→ word jumps, ⌘⌫ delete-to-line-start, with all Shift-selection variants free.

## What's implemented

| Layer | What you get |
|---|---|
| 1. Modifier remap | Mac modifier row via keyd layers |
| 2. Launcher | ⌘Space → [Vicinae](https://github.com/vicinaehq/vicinae) (Spotlight/Raycast), ⌥Space → KRunner backup |
| 3. Text editing | ⌥/⌘ word, line, and document navigation + deletion, Shift-selection included |
| 4. ⌘Tab | Held-modifier app switcher via keyd `swapm()` into KWin's switcher |
| 5. ⌘W / ⌘Q | Close tab per-app; close window compositor-wide |
| 6. Screenshots + Spaces | ⇧⌘3/4/5/6 → Spectacle; ⌃←/→ desktops; ⌃↑ Mission Control; ⌃↓ App Exposé |
| 7. App conveniences | ⌘, preferences; selection-aware ⌘C/⌘V in Konsole (Ctrl-C still interrupts) |
| 8. Desktop behaviors | Double-click-minimize titlebars, double-click open, top-right notifications |
| 9. Time Machine | snapper hourly snapshots of /home with Apple's retention curve; bootable root snapshots |
| 10. Menu bar | Global menu with bold app name, flush full-width panel, Dim Inactive for focus visibility |
| 11. Rectangle | All 22 default shortcuts via the **Cupertino Rectangle** KWin script (below) |

The full implementation notes — every file touched, every trade-off, every debugging lesson — live in [docs/cupertino-layer.md](docs/cupertino-layer.md).

## Cupertino Rectangle

A self-contained KWin script (`kwin-scripts/cupertino-rectangle/`) implementing Rectangle.app's default actions with Rectangle's geometry semantics, including per-window Restore memory. On the keyd layout, Rectangle's ⌃⌥ chord is physical **Ctrl+Super**:

| Action | ⌃⌥ + |
|---|---|
| Halves | ← → ↑ ↓ |
| Corners | U I J K |
| Thirds / Two-thirds | D F G / E R T |
| Maximize / Max height | Return / ⇧↑ |
| Smaller / Larger / Center / Restore | − / = / C / ⌫ |
| Next / Previous display | ⌘→ / ⌘← |

It works standalone on any Plasma 6 setup too (the chords are KDE-side `Meta+Alt+…`):

```bash
kpackagetool6 -t KWin/Script -i kwin-scripts/cupertino-rectangle
kwriteconfig6 --file kwinrc --group Plugins --key cupertino-rectangleEnabled true
qdbus6 org.kde.KWin /KWin reconfigure
```

## Installing the keyd layer

> ⚠️ **Read this first.** A bad keyboard config can lock you out of your keyboard. keyd's panic exit is **Backspace+Escape+Enter** (terminates keyd, restoring plain keys). And on keyd 2.6.0 with this layered config, **never `keyd reload`** — it segfaults the daemon; always `keyd check` then restart the service.

```bash
sudo pacman -S keyd            # or your distro's package
sudo cp keyd/default.conf /etc/keyd/default.conf
keyd check /etc/keyd/default.conf && sudo systemctl enable --now keyd || sudo systemctl restart keyd
```

Everything else (shortcuts, panels, snapshots) is currently hand-applied — [docs/cupertino-layer.md](docs/cupertino-layer.md) has the exact commands for each layer.

## Roadmap

- **The installer** — one script, per-layer opt-in, with toggles for taste (hot corners, natural scrolling, …)
- **Vicinae deep-dive** — clipboard history, snippets, calculator, extension hotkeys
- **Fullscreen ⌃⌘F** — macOS-style fullscreen-to-its-own-Space (KWin script)
- **External backup** — btrbk to an external drive, completing the Time Machine story

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Especially wanted: testing on non-CachyOS distros, the installer, and KWin-script review. The [implementation notes](docs/cupertino-layer.md) double as a contributor's guide to *why* everything is the way it is, including the hard-won lessons (keyd composite-layer rules, KWin's silently-missing `Qt.rect()`, Qt keycode traps).

## License

[MIT](LICENSE)
