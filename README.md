# kupertino

**macOS keyboard shortcuts for KDE Plasma — keyd layers, KWin scripts, and muscle-memory parity.**

kupertino does one thing: it makes your fingers work on KDE Plasma the way they work on a Mac. ⌘C/⌘V with Command next to the spacebar, ⌘Tab app switching, ⌥-word / ⌘-line text navigation, ⌘W/⌘Q close semantics, ⇧⌘4 screenshots, Control-arrow Spaces, and all 22 of [Rectangle.app](https://github.com/rxhanson/rectangle)'s window-management shortcuts.

It is deliberately **not** a theme and not a desktop makeover. No icons, no panels, no visual changes — if you want Plasma to *look* like macOS, [MacTahoe-kde](https://github.com/vinceliuice/MacTahoe-kde) does that beautifully and composes fine with this. kupertino is the half nobody had built: making Plasma *feel* like macOS under your hands.

Built and daily-driven on **CachyOS + KDE Plasma 6 (Wayland)**.

## Install

```bash
git clone https://github.com/beansnr1ce/kupertino
cd kupertino && ./install.sh
```

The installer walks you through every feature below, then shows the resulting plan and asks you to **authorize each step individually** — package installs (keyd, and Spectacle if missing), the keyd config, each set of KDE bindings. Nothing touches your system until you approve it, the keyd config is validated with `keyd check` before it's installed, and a failed step aborts everything after it. Python 3 stdlib only.

**v1.0 targets CachyOS / Arch-based KDE Plasma** (verified end-to-end on a fresh Arch system). On other distros the installer still generates and validates configs, but skips package installs with a warning — install keyd yourself first. Known status from our container tests: openSUSE packages keyd; Fedora needs the `alternateved/keyd` COPR; **Ubuntu 24.04 LTS has no keyd package** (Ubuntu 24.10+/Debian 13 do).

> ⚠️ A bad keyboard config can lock you out of your keyboard. keyd's panic exit is **Backspace+Escape+Enter** (terminates keyd, restoring plain keys). If you ever edit the config by hand: **never `keyd reload`** — it segfaults keyd 2.6.0 with layered configs; always `keyd check` then `sudo systemctl restart keyd`.

## How it works

One idea, applied consistently: **remap once, at the lowest level, and let everything above adapt.**

[keyd](https://github.com/rvaiya/keyd) rewrites modifiers at the kernel-input level so the physical modifier row mirrors a Mac's — Control, Option, Command reading toward the spacebar:

| You physically press | Apps/KDE see | macOS role |
|---|---|---|
| Ctrl (corner) | **Meta** | ⌃ Control — window management, Spaces |
| Super/Win | **Alt** | ⌥ Option — word-wise movement |
| Alt (next to space) | **Ctrl** | ⌘ Command — shortcuts |

Everything else — KWin shortcuts, Spectacle bindings, the Cupertino Snap script — is configured in *post-remap* terms on top of that foundation. keyd layers (not plain swaps) add the macOS text-editing behaviors: ⌘←/→ line jumps, ⌥←/→ word jumps, ⌘⌫ delete-to-line-start, with all Shift-selection variants free.

## The shortcuts

| macOS habit | Status |
|---|---|
| ⌘C/V/X/A/S/Z, ⇧⌘Z — with ⌘ next to the spacebar | ✅ base remap |
| ⌥←/→ word jumps, ⌘←/→ line jumps, ⌘↑/↓ doc jumps, ⌥⌫/⌘⌫ deletion, all ⇧-selection variants | ✅ keyd layers |
| ⌘Tab / ⌘` — held-modifier app and window switching | ✅ keyd `swapm()` → KWin switcher |
| ⌘W close tab, ⌘Q close window (compositor-wide, prompts intact) | ✅ |
| ⇧⌘3/4/5/6 — screen, region, capture UI, active window | ✅ Spectacle |
| ⌃←/→ Spaces, ⌃↑ Mission Control, ⌃↓ App Exposé | ✅ KWin |
| ⌘, opens preferences; selection-aware ⌘C/⌘V in the terminal (Ctrl-C still interrupts) | ✅ |
| Rectangle-style window snapping: halves, corners, thirds, two-thirds, maximize, center, restore, displays | ✅ Cupertino Snap (below) |
| ⌘Space launcher | 🔜 binding recipe documented; launcher choice open — see [Roadmap](#roadmap) |
| ⌃⌘F fullscreen-to-its-own-Space | 🔜 needs a KWin script |

The full implementation notes — every file touched, every trade-off, every debugging lesson — live in [docs/cupertino-layer.md](docs/cupertino-layer.md). (The notes also cover a few reference-machine extras beyond kupertino's scope — snapshots, panel arrangement, desktop behaviors — kept for context.)

## Cupertino Snap

A self-contained KWin script (`kwin-scripts/cupertino-snap/`) implementing all 22 of [Rectangle.app](https://github.com/rxhanson/rectangle)'s default actions with Rectangle's geometry semantics, including per-window Restore memory — so mac window-management muscle memory transfers intact. (Not affiliated with or endorsed by Rectangle.app; this is an independent reimplementation of its default shortcuts.) On the keyd layout, Rectangle's ⌃⌥ chord is physical **Ctrl+Super**:

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
kpackagetool6 -t KWin/Script -i kwin-scripts/cupertino-snap
kwriteconfig6 --file kwinrc --group Plugins --key cupertino-snapEnabled true
qdbus6 org.kde.KWin /KWin reconfigure
```

## Roadmap

- **The launcher (⌘Space)** — the Spotlight/Raycast slot is deliberately unfilled. Candidates to evaluate before committing: [Vicinae](https://github.com/vicinaehq/vicinae), [Albert](https://github.com/albertlauncher/albert), [Ulauncher](https://github.com/Ulauncher/Ulauncher), or a tuned KRunner. Opinions and comparisons welcome in issues.
- **Fullscreen ⌃⌘F** — macOS-style fullscreen-to-its-own-Space (KWin script)

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Especially wanted: testing on non-CachyOS distros, the installer, and KWin-script review. The [implementation notes](docs/cupertino-layer.md) double as a contributor's guide to *why* everything is the way it is, including the hard-won lessons (keyd composite-layer rules, KWin's silently-missing `Qt.rect()`, Qt keycode traps).

## License

[MIT](LICENSE)
