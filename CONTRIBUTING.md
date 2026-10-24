# Contributing to kupertino

Thanks for the interest! This project is young — extracted from one working machine — so there's plenty of high-impact work.

## Where help is most wanted

1. **Distro support beyond CachyOS/Arch.** Open an issue with your distro, Plasma version, and what broke.
2. **The installer.** `installer.py` (run via `./install.sh`) is stdlib-only Python, built test-first. Its functional core — keyd config assembly, plan building, the wizard, authorization, execution — is covered in `tests/test_installer.py`; the imperative shell (`detect_system`/`main`, real sudo/subprocess/D-Bus) is deliberately untested and verified by hand. Run the suite with `python3 -m unittest discover -s tests`. PRs touching the core should come with tests; expected values must come from a verified working config, not from re-running the code's own logic.
3. **Cupertino Snap review.** `kwin-scripts/cupertino-snap/` is a self-contained KWin script; KWin-scripting expertise (multi-monitor edge cases, per-desktop behavior) is appreciated.
4. **The launcher decision.** The ⌘Space Spotlight/Raycast slot is deliberately unfilled — comparisons of Vicinae, Albert, Ulauncher, tuned KRunner, and anything else worth considering are welcome as issues. May explore all of these as specific options to install as part of the script. 
5. **Missing macOS behaviors.** Fullscreen-to-its-own-Space (⌃⌘F) is the biggest open item.

## Ground rules

- **Read [docs/kupertino-layer.md](docs/kupertino-layer.md) first.** It explains every decision and documents the traps (keyd composite layers can't carry modifier tags; `Qt.rect()` doesn't exist in KWin JS; Qt arrow keycodes are Left/Up/Right/Down, not Left/Right adjacent; `keyd reload` segfaults 2.6.0 with layered configs). Don't re-lose battles that are already won.
- **Keyboard shortcuts, muscle memory, and the Kupertino Global Theme — that's the whole scope.** The theme (`look-and-feel/`) is Breeze Dark plus the menu bar and dock layout. macOS look-alike visuals (icons, cursors, window decorations) are out of scope, since MacTahoe and WhiteSur already do that well and Kupertino is meant to switch cleanly with them. Non-keyboard features (snapshots/backup, file sharing) are also out. The implementation notes mention some of those as reference-machine context; that doesn't make them project scope.
- **The layout stays stock.** The theme's panels use stock Plasma widgets only. Third-party plasmoids and widget theming stay out.
- **Every change reversible and documented** — one config file or one setting where possible, with the file it touches and why noted in the docs. Anything new the installer writes needs a matching revert in `build_uninstall_plan`, keyed on kupertino's exact value so user changes survive.
- **Layer discipline.** Key remapping happens once, in keyd. Everything above configures in post-remap terms. PRs that fight the remap instead of adapting to it will be asked to restructure.

## Testing keyd changes safely

```bash
keyd check /etc/keyd/default.conf   # validate before applying
sudo systemctl restart keyd          # never `keyd reload`
```

Panic exit if a config locks up input: **Backspace+Escape+Enter**.
