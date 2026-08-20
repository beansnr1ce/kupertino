# Cupertino Layer — implementation notes

The living implementation doc behind kupertino: every layer, every file touched, every trade-off, and the debugging lessons learned along the way. Written against the reference machine and updated as changes land there; treat paths and versions as that machine's, not universal.

**Reference machine:** CachyOS, KDE Plasma 6.7.4 (Wayland), kernel `linux-cachyos`

> **Scope note:** kupertino's scope is **keyboard shortcuts and muscle memory** (Layers 1–7 and 11). Layers 8–10 (desktop behaviors, btrfs snapshots, menu bar) are reference-machine extras documented for context — they are not part of the project.
**Last updated:** 2026-08-20 (Cupertino Snap rename)

---

## Philosophy

Don't theme Linux to *look* like macOS — make it *behave* like macOS where muscle memory matters, using the smallest change that works. Every change should be:

- **Reversible** — one config file or one setting, easy to undo.
- **Documented here** — with the file it touched and why.
- **Layered correctly** — key remapping happens once, at the lowest level (keyd), and everything above adapts to it rather than fighting it.

## Layer 1: The keyboard remap (keyd)

The foundation of the whole setup. macOS puts ⌘ (Command) next to the spacebar and uses it for shortcuts (⌘C, ⌘V, ⌘Space); PC layouts put Ctrl in the corner. keyd swaps Alt and Ctrl at the kernel-input level, so the key in the ⌘ position acts as Ctrl system-wide.

- **Package:** `keyd 2.6.0-5.1` (pacman), service enabled (`systemctl status keyd`)
- **Config:** `/etc/keyd/default.conf` (backup of the plain-swap version at `default.conf.bak`)

The config uses **layers** rather than a plain key swap: each physical modifier becomes a layer that acts as its swapped counterpart for everything, except a handful of keys that get macOS text-editing behavior (see Layer 3).

The modifier row mirrors a Mac's physical order — Control, Option, Command reading toward the spacebar:

```ini
[ids]
*

[main]
leftalt = layer(cmd)
leftmeta = layer(opt)
leftcontrol = layer(meta)

# Physical Alt = macOS Command (acts as Ctrl, plus mac text navigation)
[cmd:C]
tab = swapm(app_switch, M-tab)
grave = swapm(app_switch, M-grave)
left = home
right = end
up = C-home
down = C-end
backspace = macro(S-home backspace)

# Physical Win = macOS Option (acts as Alt, plus word-wise movement)
[opt:A]
left = C-left
right = C-right
backspace = C-backspace
delete = C-delete

# Held-Meta layer for the window switcher: entered from cmd+tab / cmd+grave,
# stays active while physical Alt is held so KWin's switcher stays open
[app_switch:M]
```

- **Validate before applying:** `keyd check /etc/keyd/default.conf`
- **Apply changes:** `sudo systemctl restart keyd` — **never `keyd reload`**: on keyd 2.6.0 the live-reload path segfaults the daemon with this layered config (verified 2026-08-18: reload → SIGSEGV core dump; a fresh service start with the identical config works fine). If keyd dies, the keyboard silently falls back to unswapped keys.
- **Panic exit:** keyd's built-in escape hatch is `Backspace+Escape+Enter`, which terminates keyd if a config ever locks up input.

### The mental model (important)

keyd sits below everything, so **every application and KDE setting sees the swapped keys**. When configuring any shortcut, translate first:

| You physically press | Apps/KDE see | macOS equivalent |
|---|---|---|
| Ctrl (corner) | **Meta** | Control (window management / Spaces) |
| Win (right of Ctrl) | **Alt** | ⌥ Option |
| Alt (next to space) | **Ctrl** | ⌘ Command |

**Rule of thumb: to bind something to the physical ⌘-position key, configure it as `Ctrl+…` in KDE / the app.** Shortcuts shown in KDE System Settings are in *post-remap* terms, not physical keys.

Side effects of physical Ctrl emitting Meta: all KWin shortcuts (`Meta+W` overview, `Meta+D` peek desktop, `Meta+Tab` window walk, …) sit on the physical Ctrl key, and a bare Ctrl tap opens the Kickoff menu (KDE's Meta-tap binding).

## Layer 2: App launcher (Spotlight equivalent) — not in kupertino yet

Goal: physical **Alt+Space** (the ⌘Space position) opens a launcher, like Spotlight.

**Deliberately not part of kupertino for now.** The reference machine runs [Vicinae](https://github.com/vicinaehq/vicinae) on physical Alt+Space (registered KDE-side as `Ctrl+Space` — see mental model above) with KRunner as a backup on physical Win+Space, but the project hasn't committed to a launcher: alternatives (Vicinae, Albert, Ulauncher, a tuned KRunner) need evaluating first. See Known gaps.

Whatever wins, the wiring is one `kglobalshortcutsrc` entry under `[services][<launcher>.desktop]` set to `Ctrl+Space`, applied with the recipe below.

### How to change KDE global shortcuts from the CLI

On Plasma 6.7, **KWin itself owns the global-shortcut service** (`org.kde.kglobalaccel` on the session bus); the old `kglobalacceld` daemon is vestigial and exits immediately if started. Restarting services doesn't reload shortcuts — apply them live over D-Bus:

```bash
# 1. Persist to config (survives reboot)
kwriteconfig6 --file kglobalshortcutsrc \
  --group services --group <component>.desktop \
  --key <action> "<KeySequence>"

# 2. Apply live (no logout needed) — keys are Qt keycodes
busctl --user call org.kde.kglobalaccel /kglobalaccel \
  org.kde.KGlobalAccel setForeignShortcut asai \
  4 "<component>.desktop" "<action>" "" "" 1 <qt-keycode>
```

Useful Qt keycodes: `Ctrl+Space` = `67108896` (0x04000020), `Alt+Space` = `134217760` (0x08000020). Modifier masks: Ctrl `0x04000000`, Alt `0x08000000`, Meta `0x10000000`, Shift `0x02000000`; add the key's code (Space = `0x20`).

⚠️ Arrow-key codes are **not** in left/right pairs — the order is Left `0x01000012`, **Up `0x01000013`**, Right `0x01000014`, Down `0x01000015` (this once cost us a debugging session — Right got registered as Meta+Up). Audit any key with:
`busctl --user call org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel globalShortcutsByKey '(ai)(i)' 4 <keycode> 0 0 0 0` — it lists every action registered on that key, which also exposes conflicts.

Shifted digits are ambiguous: register **all** forms (`Ctrl+Shift+3`, `Ctrl+Shift+#`, `Ctrl+#`) — KWin matched the symbol form in practice.

Multiple shortcuts for one action are tab-separated in `kglobalshortcutsrc` (stored as `\t`).

## Layer 3: macOS text-editing shortcuts

Implemented inside the keyd layers above. In physical-key terms:

| macOS habit | Physical keys | What apps receive |
|---|---|---|
| ⌥ ←/→ — word jump | Win + ←/→ | `Ctrl+Arrow` |
| ⌥ ⌫ — delete word back | Win + Backspace | `Ctrl+Backspace` |
| ⌥ Del — delete word forward | Win + Delete | `Ctrl+Delete` |
| ⌘ ←/→ — line start/end | Alt + ←/→ | `Home` / `End` |
| ⌘ ↑/↓ — doc start/end | Alt + ↑/↓ | `Ctrl+Home` / `Ctrl+End` |
| ⌘ ⌫ — delete to line start | Alt + Backspace | `Shift+Home, Backspace` macro |

All **Shift selection variants work automatically** (⇧⌘→ selects to line end, ⇧⌥← selects previous word, …) because keyd passes held Shift through the layer mappings.

Already working via the base swap, no extra config: ⌘C/V/X/A/S, ⌘Z undo, ⇧⌘Z redo.

### Caveats

- **Terminals:** the ⌘⌫ macro (`Shift+Home, Backspace`) doesn't delete-to-line-start in shells; use the shell-native `Ctrl+U` (physical Alt+U) instead.
- **Browser Back:** Linux browsers bind Back to `Alt+←`, which nothing emits anymore. Firefox supports `Ctrl+[` = physical Alt+[ — same as macOS ⌘[. Carve out a keyd exception if this becomes annoying.
- Emacs-style `Ctrl+A/E/K` (macOS supports natively) deliberately **not** implemented — the Ctrl modifier is produced by the physical Alt (⌘) key, where Ctrl+A already means select-all.

## Layer 4: ⌘Tab app switching

Physical **Alt+Tab** (⌘Tab) opens KWin's window switcher and keeps it open while Alt is held — tap Tab to cycle, Shift+Tab to reverse, release to commit. Physical **Alt+`** (⌘`) cycles windows of the current application.

**How it works:** a plain remap can't do this — the switcher needs its modifier *held*. keyd's `swapm()` handles it: pressing Tab inside the `cmd` layer swaps to the `app_switch` layer (which holds Meta) and fires `Meta+Tab`; the layer stays active until the physical Alt key is released, so KWin sees Meta held throughout. KWin's existing bindings (`Meta+Tab` walk windows, `` Meta+` `` walk current app's windows) are the targets — no KDE-side changes were needed.

**Trade-offs:**

- Physical Alt+Tab no longer emits `Ctrl+Tab` (browser next-tab). Use ⌘1–9 (physical Alt+number → `Ctrl+number`) for browser tabs, as on macOS.
- KWin walks *windows*, not grouped *applications* like macOS ⌘Tab — closest out-of-the-box behavior.
- Physical Ctrl+Tab (Meta+Tab directly) still walks windows too.

## Layer 5: ⌘W / ⌘Q close semantics

- **⌘W (physical Alt+W)** — no config needed: it emits `Ctrl+W`, the standard close-tab/close-document shortcut in browsers and KDE apps. Deliberately **not** bound globally in KWin — a global binding would close the whole window and break per-app tab closing.
- **⌘Q (physical Alt+Q)** — emits `Ctrl+Q`, now added to KWin's **Window Close** action alongside `Alt+F4`. The compositor handles it before apps do (Wayland), so it uniformly closes the focused window everywhere, regardless of whether the app binds Ctrl+Q itself. Apps still receive a normal close request, so unsaved-changes prompts work.
  - Applied via `setForeignShortcut` on component `kwin`, action `Window Close`; persisted in `[kwin]` `Window Close=Alt+F4\tCtrl+Q,...`. Qt keycodes: `Alt+F4` = 150994995, `Ctrl+Q` = 67108945.

**Trade-offs:**

- KWin shadows app-level `Ctrl+Q`: Firefox's "quit all windows" becomes "close this window" — macOS-flavored ⌘Q quits-the-app behavior only truly matches for single-window apps.
- In terminals, ⌘W reaches the shell as `Ctrl+W` (readline kill-word) instead of closing the tab — same terminal caveat family as ⌘⌫.

## Layer 6: Screenshots and Spaces

### Screenshots (⇧⌘3 / ⇧⌘4 / ⇧⌘5)

Spectacle actions gained macOS bindings alongside their KDE defaults (`Shift+Print` etc. still work):

| macOS habit | Physical keys | Spectacle action |
|---|---|---|
| ⇧⌘3 — capture full screen | Shift+Alt+3 | `FullScreenScreenShot` |
| ⇧⌘4 — capture region | Shift+Alt+4 | `RectangularRegionScreenShot` |
| ⇧⌘5 — capture/record UI | Shift+Alt+5 | `_launch` (opens Spectacle) |
| ⇧⌘6 — capture active window | Shift+Alt+6 | `ActiveWindowScreenShot` (our extension — macOS uses ⇧⌘4-then-Space, which has no KDE equivalent) |

Each is registered in **both** the digit form (`Ctrl+Shift+3`) and the shifted-symbol form (`Ctrl+Shift+#`), because shifted number keys can report either way — component `org.kde.spectacle.desktop` in `kglobalshortcutsrc`.

### Desktop switching (⌃←/→, macOS Spaces)

- Created 4 virtual desktops (was 1) — via `qdbus6 org.kde.KWin /VirtualDesktopManager createDesktop` (a `kwinrc` `Number=` edit + reconfigure does **not** create them).
- **Physical Ctrl+←/→** (KDE-side `Meta+←/→`) switches desktops, matching macOS Control+arrows.
- Window quick-tiling, which previously owned `Meta+←/→`, moved to KDE-side `Meta+Ctrl+←/→` = **physical Ctrl+Alt+←/→** — a clean swap, since that combo was the old (now redundant) desktop-switch binding. Quick-tile up/down and drag-to-edge snapping unchanged.

### Mission Control (⌃↑ / ⌃↓)

- **Physical Ctrl+↑** (KDE-side `Meta+Up`) → KWin **Overview** (Mission Control equivalent; `Meta+W` still works too)
- **Physical Ctrl+↓** (KDE-side `Meta+Down`) → **Present Windows, current app** (App Exposé; KWin action `ExposeClass`)
- All four **quick-tile directions** now live on KDE-side `Meta+Ctrl+arrows` = **physical Ctrl+Alt+arrows** (up/down joined left/right; the up/down slots were freed by clearing "Switch One Desktop Up/Down", which is meaningless in a single-row desktop layout). This round also fixed yesterday's left/right tile codes, which were missing the arrow-key bit (`0x01000000`) and bound to garbage — correct arrow codes with Meta+Ctrl are `0x15000012–15`.

### Considered, not implemented

- **Emoji picker (⌃⌘Space):** KDE's picker exists on `Meta+.`; a `Ctrl+Meta+Space` binding would match macOS exactly. Skipped — not used enough to justify. Log kept here in case that changes.
- **Force Quit (⌘⌥⎋) — needs design thought first.** The mechanical binding is easy (KWin "Kill Window" on KDE-side `Ctrl+Alt+Esc`), but the semantics don't transfer: Linux apps die with their last window (closing Brave's window quits Brave), whereas macOS keeps apps alive windowless — so "force quit a running-but-windowless app" isn't a thing here, and kill-window may be all we'd ever need. Revisit if a hung-app workflow emerges.
- **Fullscreen (⌃⌘F):** KWin's "Window Fullscreen" action is unbound and physical Ctrl+Alt+F (`Meta+Ctrl+F`) is free — but KWin fullscreens *in place*; it does not create a dedicated desktop per fullscreen window the way macOS Spaces does. Replicating that needs a custom KWin script (move window to new desktop on fullscreen, clean up on exit). Deferred: fullscreen will be handled as part of a planned **Rectangle-style window-management project** (separate effort, not yet started).

## Layer 7: App conveniences

### ⌘, — preferences (keyd)

`comma = C-S-comma` in the `[cmd:C]` layer: physical Alt+, emits `Ctrl+Shift+,`, KDE's standard "Configure Application" shortcut, so ⌘, opens settings in every KDE app. **Trade-off:** apps that natively use `Ctrl+,` for settings (VS Code) now receive `Ctrl+Shift+,` instead — rebind inside those apps if it grates.

### ⌘C / ⌘V in Konsole

Konsole's Copy/Paste actions rebound to `Ctrl+C` / `Ctrl+V` via `~/.local/share/kxmlgui5/konsole/sessionui.rc` (KXmlGui `ActionProperties` override — survives Konsole upgrades). The magic that makes this safe: **Konsole only enables its Copy action while text is selected**, so Ctrl+C with no selection falls through to the shell as SIGINT — same feel as macOS where ⌘C copies and Ctrl-C interrupts.

- Costs: shell loses `Ctrl+V` literal-insert (readline `quoted-insert`); use `Ctrl+Shift+V` still works for paste too.
- Existing Konsole windows keep old shortcuts until restarted; new windows/tabs pick it up.

### Screen lock — decided: keep as-is

Physical Ctrl+L (KDE `Meta+L`) locks the screen. Considered moving to macOS's ⌃⌘Q; decided to keep.

## Layer 8: Desktop behaviors

- **Titlebar double-click minimizes** (macOS-style) instead of maximizing — `kwinrc` `[Windows]` `TitlebarDoubleClickCommand=Minimize`.
- **Double-click opens files** — `kdeglobals` `[KDE]` `SingleClick=false` (set explicitly; matches macOS).
- **Notifications appear top-right** — `plasmanotifyrc` `[Notifications]` `PopupPosition=TopRight`.
- **System tray added to the top panel** (widget 75, between global menu and clock — mac menu-bar order). Discovery: this machine had **no system tray anywhere**, and Plasma's notification service lives inside it, so notification popups had never worked (`org.freedesktop.Notifications` had no owner and activation timed out). Adding the tray fixed notifications entirely.
- **AirDrop parity: LocalSend** (installed, `localsend 1.17.0`) — preferred over KDE Connect.

## Layer 9: Time Machine (btrfs snapshots)

CachyOS ships the full snapshot stack; this layer turned on the half that protects *user files*. The mapping:

| macOS | Here |
|---|---|
| APFS local snapshots (hourly, auto-thinned) | snapper `home` config, hourly timeline on `/home` |
| "Reinstall from a snapshot" recovery | snap-pac pre/post snapshots of `/` on every pacman transaction, **bootable** from the Limine boot menu → Snapshots (limine-snapper-sync) |
| Time Machine browser | BTRFS Assistant (GUI), or `/home/.snapshots/<N>/snapshot/...` directly |
| External-drive backup | **Not covered** — snapshots live on the same disk. Future: `btrbk` to USB. |

Setup (2026-08-19): created snapper config `home` for `/home` (own subvolume `@home` — root snapshots never touched it), Time Machine retention curve (`TIMELINE_LIMIT_HOURLY=24, DAILY=30, WEEKLY=8, MONTHLY=12`), `ALLOW_USERS=<your-user>` + `SYNC_ACL=yes` so snapshots browse without sudo, enabled `snapper-timeline.timer`. Root config left as shipped (pacman-event snapshots only; timeline off on purpose).

Recovery moves:
- **Old version of a file:** copy it out of `/home/.snapshots/<N>/snapshot/...`, or use BTRFS Assistant.
- **Undo changes to a folder:** `snapper -c home undochange <N>..0 /home/<you>/somedir`
- **System rollback:** reboot → Limine → Snapshots → pick a pre-update snapshot.

Ops note: `limine-snapper-sync.service` shows *inactive* — expected. `inotify-tools` isn't installed, so it falls back to snapper plugin integration (CachyOS default): boot entries sync on every snapshot event anyway.

## Layer 10: Menu bar polish + active-window visibility

- **Bold app name in the menu bar** (macOS's **Finder** File Edit…) — third-party widget [Window Title Applet 6](https://github.com/dhruv8sh/plasma6-window-title-applet) (plugin id `org.kde.windowtitle`, the Plasma 6 continuation of psifidotos' applet), installed per-user via `kpackagetool6 -t Plasma/Applet -i` (lives in `~/.local/share/plasma/plasmoids/`, survives Plasma upgrades but is third-party code). Widget 92, leftmost on the top panel (`AppletOrder=92;49;75;72`), configured `txt=%a`, `isBold=true`, `noIcon=true`.
- **Top panel de-floated** — mac menu bar is flush and full-width, not a hovering pill: `plasmashellrc` `[PlasmaViews][Panel 48]` `floating=0`. The bottom dock stays floating — the mac Dock *does* float.
- **Active window pops** — KWin **Dim Inactive** effect: unfocused windows dim 20%, so focus is always obvious (something macOS itself no longer does well). `kwinrc` `[Plugins] diminactiveEnabled=true`, `[Effect-diminactive] Strength=20`, panels/desktop/keep-above excluded.
- **Global-menu limitation (inherent):** menus only appear for apps that export them — Qt/KDE and most GTK apps do (`appmenu-gtk-module` installed); Chromium/Electron apps (Brave, LocalSend) never will, on any Linux.
- **KDE Connect removed** — LocalSend is the AirDrop answer; kdeconnect uninstalled (`pacman -Rns kdeconnect`, nothing depended on it) and its tray icon with it.

## Layer 11: Rectangle-style window management (Cupertino Snap)

All of [Rectangle.app](https://github.com/rxhanson/rectangle)'s default keyboard shortcuts, implemented as a custom KWin script — **Cupertino Snap** (`~/.local/share/kwin/scripts/cupertino-snap/`, enabled via `kwinrc` `[Plugins] cupertino-snapEnabled=true`). Renamed from "Cupertino Rectangle" 2026-08-20 (see [rectangle-naming-research.md](rectangle-naming-research.md)); the shortcut *internal* action names keep their original `Rectangle*` ids so existing `kglobalshortcutsrc` registrations survive — only display labels ("Snap: Left Half") and the package id changed. KWin has native tiling for halves only; the script implements all 22 actions with Rectangle's geometry semantics, including per-window Restore memory.

Rectangle's ⌃⌥ chord = physical **Ctrl+Super** (the two bottom-left modifiers); ⌃⌥⌘ adds physical Alt. KDE-side that's `Meta+Alt` / `Meta+Alt+Ctrl`.

| Action | Physical keys (⌃⌥ = Ctrl+Super) |
|---|---|
| Halves | Ctrl+Super+ ← → ↑ ↓ |
| Corners (TL/TR/BL/BR) | Ctrl+Super+ U I J K |
| Thirds (first/center/last) | Ctrl+Super+ D F G |
| Two-thirds (first/center/last) | Ctrl+Super+ E R T |
| Maximize / Maximize Height | Ctrl+Super+Enter / Ctrl+Super+Shift+↑ |
| Make Smaller / Larger (30px steps) | Ctrl+Super+ − / = |
| Center | Ctrl+Super+C |
| Restore (pre-Rectangle geometry) | Ctrl+Super+Backspace |
| Next / Previous Display | Ctrl+Super+Alt+ → / ← |

Supporting keyd config: the `[meta+opt]` composite layer maps every Rectangle key explicitly to `M-A-*` (composite layers can't carry a modifier tag in keyd 2.6, and without explicit entries the `[opt:A]` text-navigation overrides hijack the arrows/backspace). `[meta+cmd]` similarly protects quick-tile's arrows; `[meta+opt+cmd]` carries the display moves.

Cleared to make room (all KDE-side `Meta+Alt`): directional focus switching ("Switch to Window Left/…" — macOS has no equivalent), keyboard-layout cycling (single `us` layout), Spectacle full-record on Meta+Alt+R (recording lives in the ⇧⌘5 panel). Native quick-tile stays on physical Ctrl+Alt+arrows as a KWin-flavored alternative.

**Hard-won KWin-scripting lessons:**
- `Qt.rect()` does not exist in KWin's pure-JS environment — callbacks die on a *silent* ReferenceError (nothing in the journal). Assign a plain `{x, y, width, height}` object to `frameGeometry` instead.
- `registerShortcut`'s default key only applies on first registration; changing it later requires `setForeignShortcut` + editing `kglobalshortcutsrc` (entries are `active,default,description` under `[kwin]`).
- Debug loop: `qdbus6 org.kde.KWin /Scripting loadScript <file> <name>` + `/Scripting/Script<id> run` + `print()` to the journal; fire actions keyboard-free with `qdbus6 org.kde.kglobalaccel /component/kwin org.kde.kglobalaccel.Component.invokeShortcut <name>`.
- Reload a script after editing: toggle its `[Plugins]` entry false→true with a `reconfigure` between.

## Accessibility parity (already native in Plasma)

Two macOS accessibility behaviors needed zero work — Plasma 6.7 ships them and they're active here:

- **Shake-to-find cursor** — shake the mouse, pointer enlarges (KWin "Shake Cursor" effect, enabled).
- **Screen zoom** — KWin Zoom effect on KDE-side `Meta+=` / `Meta+-` = **physical Ctrl+= / Ctrl+-** (macOS uses ⌥⌘=/−; the ⌃+scroll-wheel zoom variant has no KWin equivalent).

## Future: distributable config setup

Plan: package this setup as a configurable installer for other people, with per-user options. Opt-in toggles identified so far (both **off** on this machine by owner preference):

- **Hot corners** — macOS Hot Corners ≈ KDE Screen Edges; classic config puts Overview/Mission Control on a corner. (`kwinrc` `[Effect-overview]`/`ElectricBorders` territory.)
- **Natural scrolling** — macOS's default scroll direction; KDE per-device `NaturalScroll` in `kcminputrc`.

## Deliberate departures from macOS

Not everything should be mac-like. Choices that intentionally break the metaphor:

- **CachyOS launcher button on the dock** (2026-08-18): an Application Launcher (Kickoff, `org.kde.plasma.kickoff`) with the CachyOS logo (`/usr/share/icons/cachyos.svg`, icon name `cachyos`) sits at the left end of the bottom panel — too much functionality behind it to hide. Widget id 74 in `~/.config/plasma-org.kde.plasma.desktop-appletsrc`, containment 23. Same menu also opens on a bare physical-Ctrl tap (Meta tap binding).
  - Ops note: widgets can be added live via `qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript`, but *reordering* requires stopping plasmashell, editing `AppletOrder`, and starting it again — plasmashell rewrites the config from memory on shutdown, so edit only while it's stopped and match lines by content, not line number.

## Considered, not implemented: visual theming (MacTahoe)

[vinceliuice/MacTahoe-kde](https://github.com/vinceliuice/MacTahoe-kde) (2026-08-19): the full macOS Tahoe visual kit for Plasma — Plasma style, traffic-light window decorations, color schemes, Kvantum, SDDM, wallpapers, companion icon/cursor repos, optional blur (kwin-effects-forceblur, 24px corners). Decided to **stay behavior-only** — this project's philosophy holds. Logged as the go-to if that ever changes. Notes from vetting: `install.sh` only copies files (safe, applies nothing); if ever applied, use individual components — applying it as a Global Theme with "desktop layout" checked would rebuild the panels and destroy the menu-bar/dock setup.

## Known gaps / future work

- **Launcher (⌘Space):** evaluate the candidates (Vicinae, Albert, Ulauncher, tuned KRunner) and commit kupertino to one; then the deep-dive — clipboard history, snippets, calculator, file search, extension hotkeys.
- **External backup:** the other half of Time Machine — `btrbk` (or similar) sending snapshots to an external drive; local snapshots don't survive disk death.
- **Fullscreen ⌃⌘F:** the one Rectangle-adjacent item still open — macOS-style fullscreen-to-dedicated-Space needs a KWin script that moves the window to a new desktop on fullscreen and cleans up on exit.

- **Browser Back keyboard shortcut:** lost to the text-navigation layer (see Layer 3 caveats); add a per-app keyd rule for browsers if needed.

## Changelog

- **2026-08-20** — Renamed the KWin script **Cupertino Rectangle → Cupertino Snap** (package id `cupertino-snap`, labels "Snap: …"; internal `Rectangle*` action ids unchanged so shortcut registrations survive). Prompted by a naming/trademark research pass ([rectangle-naming-research.md](rectangle-naming-research.md)): descriptive "Rectangle.app-compatible" references are nominative fair use and stay; the name itself was the cautious rename. Structure decision: the script **stays in this repo** (no spin-out, no umbrella) — a KDE Store listing can publish straight from the subdirectory.
- **2026-08-19** — Layer 11 Rectangle: all 22 of Rectangle.app's default shortcuts on physical Ctrl+Super via a custom KWin script (Cupertino Rectangle) + keyd composite layers. Debugging surfaced two classics: `Qt.rect()` silently doesn't exist in KWin JS, and keyd 2.6 composite layers can't carry modifier tags (every chord key mapped explicitly instead). Quick-tile restored to physical Ctrl+Alt+arrows.
- **2026-08-19** — Layer 10 menu bar polish: bold app name leftmost in the menu bar (Window Title Applet 6, widget 92), top panel de-floated (flush like a real menu bar; dock stays floating), KWin Dim Inactive at 20% so the focused window is unmistakable, KDE Connect uninstalled (LocalSend won). Documented the Electron/Chromium global-menu limitation.
- **2026-08-19** — Layer 9 Time Machine: snapper `home` config on `/home` with Apple's retention curve (24 hourly / 30 daily / 8 weekly / 12 monthly), `snapper-timeline.timer` enabled, sudo-free browsing for your user. Root stays on pacman-event snapshots, bootable via Limine → Snapshots. Noted: local snapshots ≠ backups; btrbk-to-external logged as future work.
- **2026-08-19** — Layer 8 desktop behaviors: double-click-minimize titlebars, double-click file opening, top-right notifications. Discovered and fixed missing system tray (notifications had never worked); tray now in the top panel, menu-bar order. LocalSend noted as the AirDrop answer. Backlogged: Vicinae deep-dive, btrfs snapshots.
- **2026-08-19** — Documented accessibility parity (shake cursor + zoom already native/enabled). Seeded the "distributable config setup" plan with hot corners and natural scrolling as its first opt-in toggles (both off for this machine).
- **2026-08-19** — Layer 7: ⌘, opens preferences (keyd `comma = C-S-comma`); Konsole Copy/Paste rebound to Ctrl+C/Ctrl+V (selection-aware, SIGINT preserved); ⇧⌘6 captures the active window. Screen lock decided: stays on physical Ctrl+L.
- **2026-08-19** — Mission Control cluster: ⌃↑ → Overview, ⌃↓ → App Exposé (current app's windows); quick-tiling consolidated on physical Ctrl+Alt+arrows (all four directions, fixing yesterday's malformed left/right codes); cleared useless desktop-up/down bindings. Logged Force Quit (semantics differ on Linux — apps die with their last window) and fullscreen (KWin has no per-fullscreen Space) as open questions.
- **2026-08-19** — Fixed Layer 6 bugs: screenshot shortcuts needed the shift-less symbol forms (`Ctrl+#/$/%`) registered — KWin matches those, not `Ctrl+Shift+3`; desktop-switch/quick-tile Right was registered on the wrong keycode (Qt arrow order is Left, Up, Right, Down). Both documented in the CLI recipe section.
- **2026-08-18** — Layer 6: macOS screenshot keys (⇧⌘3/4/5 → Spectacle) and Spaces-style desktop switching (⌃←/→; 4 virtual desktops created; quick-tile L/R moved to physical Ctrl+Alt+arrows). Emoji picker considered and logged, not implemented.
- **2026-08-18** — Added the CachyOS launcher button (Kickoff with the `cachyos` icon) to the left end of the bottom dock — a deliberate non-mac departure; see "Deliberate departures".
- **2026-08-18** — ⌘Q now closes any window: added KDE-side `Ctrl+Q` to KWin's Window Close action (Layer 5). ⌘W left to per-app `Ctrl+W` handling on purpose.
- **2026-08-18** — Added ⌘Tab app switching and ⌘` same-app window cycling (Layer 4) via keyd `swapm()` into a held-Meta `app_switch` layer targeting KWin's `Meta+Tab` / ``Meta+` `` bindings. Browser tab cycling moves to ⌘1–9.
- **2026-08-18** — Corrected the modifier row to mirror a Mac's physical order (Control → Option → Command toward the spacebar): physical Ctrl now emits Meta (KWin/window management, like macOS Control), the Win key carries the Option role (Alt + word movement), physical Alt stays Command. KRunner backup moved to physical Win+Space.
- **2026-08-18** — Added macOS text-editing shortcuts (Layer 3): word jumps on physical Ctrl (⌥ role), line/doc navigation on physical Alt (⌘ role), word/line deletion. Rewrote keyd config from a plain swap to modifier layers. Discovered `keyd reload` segfaults keyd 2.6.0 with this config — use `systemctl restart keyd` instead.
- **2026-08-18** — Moved Vicinae's trigger from physical Ctrl+Space to physical Alt+Space (KDE-side `Ctrl+Space`), matching Spotlight. Added KRunner as backup launcher on physical Ctrl+Space (KDE-side `Alt+Space`). Documented the KWin/D-Bus method for setting shortcuts on Plasma 6.7.
- **~2026-08-15** — Installed keyd and enabled the Alt↔Ctrl swap in `/etc/keyd/default.conf` (predates this doc; date approximate).
