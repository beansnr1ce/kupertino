# kupertino

macOS keyboard shortcuts for KDE Plasma. Bringing some of the best of macOS (usability) to CachyOS, for those of us who enjoy using (but maybe not the visuals of) the current iteration of macOS. 

## What is kupertino?

kupertino remaps the modifier row with [keyd](https://github.com/rvaiya/keyd) and configures KWin and Spectacle so common macOS shortcuts work on Plasma, and builds a macOS-style menu bar from stock Plasma widgets. No themes or icons — for macOS visuals, you can check out [MacTahoe-kde](https://github.com/vinceliuice/MacTahoe-kde).

Built on and for CachyOS + KDE Plasma 6 (Wayland).

## Install

```bash
git clone https://github.com/beansnr1ce/kupertino
cd kupertino && ./install.sh
```

The installer asks which features you want, then asks you to confirm each step before it runs. Requires Python 3.

v1.0 supports and has been tested on CachyOS specifically.

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

Plus the menu bar (below).

Planned: ⌘Space launcher, ⌃⌘F fullscreen. Implementation notes: [docs/kupertino-layer.md](docs/kupertino-layer.md).

## Menu bar

An optional top panel that behaves like macOS's menu bar: the focused app's menus on the left, system tray and clock on the right, flush and full-width rather than a floating pill. Stock Plasma widgets only — no third-party plasmoids to break on upgrade.

The installer **skips this step if you already have a top panel**, so it won't disturb an existing layout. To build it by hand, add these to a top panel in this order:

| Widget | Why |
|---|---|
| Global Menu | The menus themselves |
| Panel Spacer (**expanding**) | Pins everything after it to the right |
| System Tray | Also hosts Plasma's notification service |
| Digital Clock | Right corner, like macOS |

The expanding spacer is not optional. The Global Menu applet is the panel's only naturally stretching element, so without a spacer the tray and clock slide left whenever the focused app exports no menu.

Apps that draw their own in-window menu bar — Steam, and Chromium/Electron apps generally — will never populate it. That's a Linux-wide limitation, not a kupertino one. GTK apps need `appmenu-gtk-module`, which the installer pulls in.

## Cupertino Snap

A KWin script (`kwin-scripts/cupertino-snap/`) implementing the default shortcuts of [Rectangle.app](https://github.com/rxhanson/rectangle) (not affiliated). This is one of my favorite macOS usability enhancements, something I rely on daily, and which I found myself missing terribly after I moved to my main PC to CachyOS. With the keyd remap, ⌃⌥ is physical Ctrl+Super.

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
