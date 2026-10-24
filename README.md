# kupertino

macOS keyboard shortcuts and a macOS-style menu bar for KDE Plasma. Bringing some of the best of macOS (usability) to CachyOS, for those of us who enjoy using (but maybe not the visuals of) the current iteration of macOS. 

## What is kupertino?

Two independent parts, installed and uninstalled as a unit or separately:

- **Keyboard:** remaps the modifier row with [keyd](https://github.com/rvaiya/keyd) and configures KWin and Spectacle so common macOS shortcuts work on Plasma. It works under any Global Theme.
- **Kupertino Global Theme:** Breeze Dark with a macOS-style menu bar and dock, built from stock Plasma widgets.

There are no macOS icons or window decorations; for those, see [MacTahoe-kde](https://github.com/vinceliuice/MacTahoe-kde) or [WhiteSur-kde](https://github.com/vinceliuice/WhiteSur-kde). You can run either of those with kupertino's keyboard part, or switch between their Global Theme and Kupertino's in System Settings.

Built on and for CachyOS + KDE Plasma 6 (Wayland).

## Install

```bash
git clone https://github.com/beansnr1ce/kupertino
cd kupertino && ./install.sh
```

The installer asks which features you want, then asks you to confirm each step before it runs. Requires Python 3. To keep your current theme (WhiteSur, say), answer `n` to the Global Theme question; nothing then touches your panels or visuals.

v1.0 supports and has been tested on CachyOS specifically.

## Uninstall

```bash
./uninstall.sh
```

It reverts only what still carries kupertino's values, so anything you've changed since is left alone. Each step asks for confirmation, so declining one keeps that part; decline the keyd step to keep the remap, for example. If Kupertino is your active Global Theme, your previous theme and panels come back; if you've switched to another theme, your look is left as it is. Installed packages and virtual desktops stay.

## Safety

If a keyd config ever locks up your keyboard, press Backspace+Escape+Enter to kill keyd. Never use `keyd reload` (it segfaults keyd 2.6.0 with layered configs); run `keyd check`, then restart the service.

## How it works

keyd remaps modifiers at the kernel level so the modifier row matches a Mac:

| Physical key | Apps/KDE see | macOS role |
|---|---|---|
| Ctrl | Meta | ⌃ Control |
| Super/Win | Alt | ⌥ Option |
| Alt | Ctrl | ⌘ Command |

KDE shortcuts and the Snap script are configured in post-remap terms on top of that.

One consequence gets cleaned up automatically: because physical Ctrl now emits Meta, KDE's Meta-tap binding would open the application launcher on every bare Ctrl tap — including crouch in a game. The installer clears it (Kickoff stays on `Alt+F1`, i.e. physical Win+F1, and on any panel launcher widget).

## Shortcuts

- ⌘C/V/X/A/S/Z, ⇧⌘Z
- ⌥←/→ word jumps, ⌘←/→ line jumps, ⌘↑/↓ document jumps, ⌥⌫/⌘⌫ deletion, all with Shift selection
- ⌘Tab / ⌘` app and window switching
- ⌘W close tab, ⌘Q close window
- ⇧⌘3/4/5/6 screenshots (Spectacle)
- ⌃←/→ desktops, ⌃↑ Overview, ⌃↓ App Exposé
- ⌘, preferences; ⌘C/⌘V in Konsole (Ctrl-C still interrupts)
- Window snapping via Cupertino Snap (below)

Plus the Global Theme's menu bar (below).

Planned: ⌘Space launcher, ⌃⌘F fullscreen. Implementation notes: [docs/kupertino-layer.md](docs/kupertino-layer.md).

## Kupertino Global Theme

Optional. Its top panel behaves like macOS's menu bar: the focused app's menus on the left, system tray and clock on the right, flush and full-width rather than a floating pill. A dock sits along the bottom, and the visuals are Breeze Dark. Stock Plasma widgets only, so there are no third-party plasmoids to break on upgrade.

Applying it **replaces your current panels**. The installer backs them up first, and `./uninstall.sh` puts them back. After that, Kupertino is an ordinary entry in System Settings → Global Theme. Tick "Desktop and window layout" when switching to it, or you get the colors without the menu bar.

To build the menu bar by hand instead, add these to a top panel in this order:

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
