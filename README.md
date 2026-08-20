# kupertino

macOS keyboard shortcuts for KDE Plasma.

kupertino remaps the modifier row with [keyd](https://github.com/rvaiya/keyd) and configures KWin and Spectacle so common macOS shortcuts work on Plasma. It changes behavior only — no themes, icons, or panel changes. For macOS visuals, see [MacTahoe-kde](https://github.com/vinceliuice/MacTahoe-kde).

Built on CachyOS + KDE Plasma 6 (Wayland).

## Install

```bash
git clone https://github.com/beansnr1ce/kupertino
cd kupertino && ./install.sh
```

The installer asks which features you want, then asks you to confirm each step before it runs. Requires Python 3.

v1.0 supports CachyOS/Arch. On other distros the installer skips package installs — install keyd yourself first (Fedora: `alternateved/keyd` COPR; Ubuntu 24.04 LTS has no keyd package, 24.10+ and Debian 13 do).

If a keyd config ever locks up your keyboard, press Backspace+Escape+Enter to kill keyd. Never use `keyd reload` (it segfaults keyd 2.6.0 with layered configs); run `keyd check`, then restart the service.

## How it works

keyd remaps modifiers at the kernel level so the modifier row matches a Mac:

| Physical key | Apps/KDE see | macOS role |
|---|---|---|
| Ctrl | Meta | ⌃ Control |
| Super/Win | Alt | ⌥ Option |
| Alt | Ctrl | ⌘ Command |

KDE shortcuts and the Snap script are configured in post-remap terms on top of that.

## Shortcuts

- ⌘C/V/X/A/S/Z, ⇧⌘Z
- ⌥←/→ word jumps, ⌘←/→ line jumps, ⌘↑/↓ document jumps, ⌥⌫/⌘⌫ deletion, all with Shift selection
- ⌘Tab / ⌘` app and window switching
- ⌘W close tab, ⌘Q close window
- ⇧⌘3/4/5/6 screenshots (Spectacle)
- ⌃←/→ desktops, ⌃↑ Overview, ⌃↓ App Exposé
- ⌘, preferences; ⌘C/⌘V in Konsole (Ctrl-C still interrupts)
- Window snapping via Cupertino Snap (below)

Planned: ⌘Space launcher, ⌃⌘F fullscreen. Implementation notes: [docs/kupertino-layer.md](docs/kupertino-layer.md).

## Cupertino Snap

A KWin script (`kwin-scripts/cupertino-snap/`) implementing the default shortcuts of [Rectangle.app](https://github.com/rxhanson/rectangle) (not affiliated). With the keyd remap, ⌃⌥ is physical Ctrl+Super.

| Action | ⌃⌥ + |
|---|---|
| Halves | ← → ↑ ↓ |
| Corners | U I J K |
| Thirds / two-thirds | D F G / E R T |
| Maximize / max height | Return / ⇧↑ |
| Smaller / larger / center / restore | − / = / C / ⌫ |
| Next / previous display | ⌘→ / ⌘← |

Works without kupertino on any Plasma 6 setup (shortcuts are `Meta+Alt+…`):

```bash
kpackagetool6 -t KWin/Script -i kwin-scripts/cupertino-snap
kwriteconfig6 --file kwinrc --group Plugins --key cupertino-snapEnabled true
qdbus6 org.kde.KWin /KWin reconfigure
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
