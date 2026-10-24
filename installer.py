#!/usr/bin/env python3
"""kupertino interactive installer and uninstaller.

Install walks through each feature, then installs the user's selections,
asking authorization for every step. Uninstall (--uninstall) reverts every
change that still carries kupertino's values, with the same per-step
authorization. Stdlib only; tests in tests/.
"""

import re
from dataclasses import dataclass, field

# --- Qt keycodes ------------------------------------------------------------
# kglobalaccel's setForeignShortcut takes raw Qt keycodes. Beware: arrow keys
# carry 0x01000000 and run Left, Up, Right, Down — not left/right adjacent.

QT_MODIFIERS = {
    "Shift": 0x02000000,
    "Ctrl": 0x04000000,
    "Alt": 0x08000000,
    "Meta": 0x10000000,
}

QT_SPECIAL_KEYS = {
    "Meta": 0x01000022,  # bare Meta, as in Plasma's default launcher tap
    "Space": 0x20,
    "Return": 0x01000004,
    "Backspace": 0x01000003,
    "Print": 0x01000009,
    "Left": 0x01000012,
    "Up": 0x01000013,
    "Right": 0x01000014,
    "Down": 0x01000015,
}
QT_SPECIAL_KEYS.update({f"F{n}": 0x01000030 + n - 1 for n in range(1, 13)})


def qt_keycode(sequence):
    """Qt keycode for a KDE key sequence like 'Meta+Ctrl+Left' or 'Ctrl+#'."""
    parts = sequence.split("+")
    # A trailing '+' key (e.g. 'Ctrl++') would split wrong; not needed yet.
    key = parts[-1]
    code = QT_SPECIAL_KEYS.get(key)
    if code is None:
        if len(key) != 1:
            raise ValueError(f"unknown key {key!r} in {sequence!r}")
        code = ord(key.upper())
    for mod in parts[:-1]:
        code += QT_MODIFIERS[mod]
    return code


# --- keyd config assembly ---------------------------------------------------
# The config is assembled from per-feature fragments. Section order and every
# line mirror the reference /etc/keyd/default.conf; with all features selected
# the output must match that file byte-for-byte (see tests).

KEYD_SECTIONS = [
    {
        "header": ["[ids]"],
        "entries": [(None, "*")],
    },
    {
        "header": ["[main]"],
        "entries": [
            (None, "leftalt = layer(cmd)"),
            (None, "leftmeta = layer(opt)"),
            (None, "leftcontrol = layer(meta)"),
        ],
    },
    {
        "header": [
            "# Physical Alt = macOS Command (acts as Ctrl, plus mac text navigation)",
            "[cmd:C]",
        ],
        "entries": [
            ("cmdtab", "tab = swapm(app_switch, M-tab)"),
            ("cmdtab", "grave = swapm(app_switch, M-grave)"),
            ("appconv", "comma = C-S-comma"),
            ("textnav", "left = home"),
            ("textnav", "right = end"),
            ("textnav", "up = C-home"),
            ("textnav", "down = C-end"),
            ("textnav", "backspace = macro(S-home backspace)"),
        ],
    },
    {
        "header": [
            "# Physical Win = macOS Option (acts as Alt, plus word-wise movement)",
            "[opt:A]",
        ],
        "entries": [
            ("textnav", "left = C-left"),
            ("textnav", "right = C-right"),
            ("textnav", "backspace = C-backspace"),
            ("textnav", "delete = C-delete"),
        ],
    },
    {
        "feature": "cmdtab",
        "header": [
            "# Held-Meta layer for the window switcher: entered from cmd+tab / cmd+grave,",
            "# stays active while physical Alt is held so KWin's switcher stays open",
            "[app_switch:M]",
        ],
        "entries": [],
    },
    {
        "feature": "rectangle",
        "header": [
            "# Rectangle chords: mac ⌃⌥ = physical Ctrl+Super. Composite layers can't",
            "# carry a modifier tag in keyd 2.6, so every Rectangle key is mapped",
            "# explicitly to Meta+Alt (overriding the [opt:A] text-navigation keys)",
            "[meta+opt]",
        ],
        "entries": [
            (None, "left = M-A-left"),
            (None, "right = M-A-right"),
            (None, "up = M-A-up"),
            (None, "down = M-A-down"),
            (None, "u = M-A-u"),
            (None, "i = M-A-i"),
            (None, "j = M-A-j"),
            (None, "k = M-A-k"),
            (None, "d = M-A-d"),
            (None, "f = M-A-f"),
            (None, "g = M-A-g"),
            (None, "e = M-A-e"),
            (None, "r = M-A-r"),
            (None, "t = M-A-t"),
            (None, "c = M-A-c"),
            (None, "enter = M-A-enter"),
            (None, "minus = M-A-minus"),
            (None, "equal = M-A-equal"),
            (None, "backspace = M-A-backspace"),
        ],
    },
    {
        "feature": "rectangle",
        "header": [
            "# Quick-tile chords: physical Ctrl+Alt+arrows → Meta+Ctrl+arrows",
            "# (the [cmd:C] arrow overrides would otherwise hijack them)",
            "[meta+cmd]",
        ],
        "entries": [
            (None, "left = M-C-left"),
            (None, "right = M-C-right"),
            (None, "up = M-C-up"),
            (None, "down = M-C-down"),
        ],
    },
    {
        "feature": "rectangle",
        "header": [
            "# Rectangle display moves: mac ⌃⌥⌘ = physical Ctrl+Super+Alt",
            "[meta+opt+cmd]",
        ],
        "entries": [
            (None, "left = M-A-C-left"),
            (None, "right = M-A-C-right"),
        ],
    },
]


# --- feature catalog and wizard ---------------------------------------------

@dataclass
class Feature:
    id: str
    title: str
    blurb: str


FEATURES = [
    Feature("remap", "The keyboard remap (foundation)",
            "keyd swaps the modifier row at the kernel level so physical "
            "Alt acts as ⌘ (Ctrl), Super as ⌥ (Alt), Ctrl as ⌃ (Meta). "
            "⌘C/V/X/A/S/Z work immediately. Everything else builds on this."),
    Feature("textnav", "macOS text editing",
            "⌥←/→ word jumps, ⌘←/→ line jumps, ⌘↑/↓ document jumps, "
            "⌥⌫/⌘⌫ deletion — Shift-selection variants included."),
    Feature("cmdtab", "⌘Tab app switching",
            "Physical Alt+Tab holds KWin's window switcher open like macOS "
            "⌘Tab; ⌘` cycles the current app's windows."),
    Feature("cmdq", "⌘Q closes the window",
            "KWin closes the focused window on ⌘Q everywhere, with "
            "unsaved-changes prompts intact. ⌘W already closes tabs."),
    Feature("screenshots", "macOS screenshot keys",
            "⇧⌘3 full screen, ⇧⌘4 region, ⇧⌘5 capture UI, ⇧⌘6 active "
            "window — all via Spectacle."),
    Feature("spaces", "Spaces & Mission Control",
            "4 virtual desktops, ⌃←/→ to switch, ⌃↑ Overview, ⌃↓ App "
            "Exposé. Window quick-tiling moves to physical Ctrl+Alt+arrows."),
    Feature("appconv", "App conveniences",
            "⌘, opens preferences in KDE apps; Konsole gets selection-aware "
            "⌘C/⌘V (Ctrl-C still interrupts when nothing is selected)."),
    Feature("rectangle", "Cupertino Snap window management",
            "All 22 Rectangle.app-compatible shortcuts on ⌃⌥ (physical Ctrl+Super): "
            "halves, corners, thirds, maximize, center, restore, displays."),
    Feature("theme", "Kupertino Global Theme",
            "A Plasma Global Theme: Breeze Dark, a flush macOS menu bar (the "
            "focused app's menus left, tray and clock right) and a dock. "
            "Replaces your current panels; they are backed up and "
            "./uninstall.sh puts them back. Switch themes any time in System "
            "Settings → Global Theme."),
]


def run_wizard(features, ask, say):
    """Walk the features; return the ids the user selected, in walk order."""
    selections = []
    for feature in features:
        say(f"\n{feature.title}\n  {feature.blurb}")
        while True:
            answer = ask(f"Enable “{feature.title}”? [y/n] ").strip().lower()
            if answer in ("y", "yes", "n", "no"):
                break
            say("Please answer y or n.")
        if answer in ("y", "yes"):
            selections.append(feature.id)
        elif feature.id == "remap":
            say("\nEvery kupertino feature builds on the keyboard remap — "
                "it's the foundation. Nothing to install without it.")
            return []
    return selections


@dataclass
class ExecutionResult:
    completed: list = field(default_factory=list)
    failed: str = None


def execute(steps, run_command, write_file, say):
    """Run approved steps in order: file write first, then each command."""
    result = ExecutionResult()
    for step in steps:
        say(f"→ {step.description}")
        if step.file_path:
            write_file(step.file_path, step.file_content)
        for argv in step.commands:
            if run_command(argv) != 0:
                result.failed = step.id
                return result
        result.completed.append(step.id)
    return result


def authorize_plan(plan, ask, say):
    """Ask the user to authorize each step; return only the approved ones."""
    approved = []
    for step in plan.steps:
        while True:
            answer = ask(f"Authorize: {step.description}? [y/n] ").strip().lower()
            if answer in ("y", "yes", "n", "no"):
                break
            say("Please answer y or n.")
        if answer in ("y", "yes"):
            approved.append(step)
    return approved


# --- plan building ----------------------------------------------------------

@dataclass
class SystemState:
    package_manager: str
    installed_packages: set
    staging_dir: str
    home: str
    repo_root: str
    konsole_sessionui_exists: bool


@dataclass
class Step:
    id: str
    description: str
    commands: list = field(default_factory=list)
    file_path: str = ""
    file_content: str = ""


@dataclass
class Plan:
    steps: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


FEATURE_PACKAGES = {
    "remap": ["keyd"],
    "screenshots": ["spectacle"],
    # Qt/KDE apps export their menus over D-Bus unaided; GTK apps need this
    # module or the menu bar stays empty for them.
    "theme": ["appmenu-gtk-module"],
}

# v1.0 targets CachyOS/Arch. --noconfirm on purpose: the user authorized the
# step already, and an interactive pacman prompt deadlocks on piped stdin
# (2026-08-20 container smoke tests). Other distros verified so far:
# openSUSE packages keyd; Fedora needs the alternateved/keyd COPR;
# Ubuntu 24.04 LTS has no keyd package at all.
PACKAGE_INSTALL = {
    "pacman": ["sudo", "pacman", "-S", "--needed", "--noconfirm"],
}


_BUSCTL = ["busctl", "--user", "call", "org.kde.kglobalaccel", "/kglobalaccel",
           "org.kde.KGlobalAccel", "setForeignShortcut", "asai", "4"]


def _binding_cmds(component, groups, key, entry):
    """kwriteconfig6 + live busctl apply for one kglobalshortcutsrc entry.

    [kwin]-style entries are 'active,default,description'; only the active
    sequences (tab-separated) are applied live.
    """
    active = entry.split(",")[0]
    sequences = active.split("\t")
    kwrite = ["kwriteconfig6", "--file", "kglobalshortcutsrc"]
    for group in groups:
        kwrite += ["--group", group]
    kwrite += ["--key", key, entry]
    bus = _BUSCTL + [component, key, "", "", str(len(sequences))]
    bus += [str(qt_keycode(s)) for s in sequences]
    return [kwrite, bus]


# Entries transcribed from the reference machine's working kglobalshortcutsrc.
SPECTACLE_BINDINGS = [
    ("FullScreenScreenShot", "Shift+Print\tCtrl+#\tCtrl+Shift+#\tCtrl+Shift+3"),
    ("RectangularRegionScreenShot",
     "Ctrl+$\tCtrl+Shift+$\tCtrl+Shift+4\tMeta+Shift+Print"),
    ("_launch", "Print\tCtrl+%\tCtrl+Shift+%\tCtrl+Shift+5\tMeta+Shift+S"),
    ("ActiveWindowScreenShot", "Ctrl+^\tCtrl+Shift+6\tCtrl+Shift+^\tMeta+Print"),
]


# Spectacle's stock shortcuts, from X-KDE-Shortcuts in its .desktop file.
# [services] entries hold only the active field, so uninstall needs these.
SPECTACLE_DEFAULTS = {
    "FullScreenScreenShot": "Shift+Print",
    "RectangularRegionScreenShot": "Meta+Shift+Print",
    "_launch": "Print\tMeta+Shift+S",
    "ActiveWindowScreenShot": "Meta+Print",
    "RecordScreen": "Meta+Alt+R",
}

CMDQ_BINDING = ("kwin", ["kwin"], "Window Close",
                "Ctrl+Q\tAlt+F4,Alt+F4,Close Window")


def _cmdq_step(system, plan):
    return Step(
        id="cmdq",
        description="Bind KDE-side Ctrl+Q (physical Alt+Q, mac ⌘Q) to KWin's "
                    "Window Close",
        commands=_binding_cmds(*CMDQ_BINDING),
    )


def _screenshots_step(system, plan):
    commands = []
    for action, entry in SPECTACLE_BINDINGS:
        commands += _binding_cmds(
            "org.kde.spectacle.desktop",
            ["services", "org.kde.spectacle.desktop"], action, entry)
    return Step(
        id="screenshots",
        description="Bind macOS screenshot keys (⇧⌘3/4/5/6) to Spectacle",
        commands=commands,
    )


# Reference-machine entries: ⌃←/→ Spaces on Meta+arrows, ⌃↑ Overview,
# ⌃↓ App Exposé, quick-tile evicted to Meta+Ctrl+arrows.
SPACES_BINDINGS = [
    ("Switch One Desktop to the Left",
     "Meta+Left,Meta+Ctrl+Left,Switch One Desktop to the Left"),
    ("Switch One Desktop to the Right",
     "Meta+Right,Meta+Ctrl+Right,Switch One Desktop to the Right"),
    ("Overview", "Meta+W\tMeta+Up,Meta+W,Toggle Overview"),
    ("ExposeClass",
     "Ctrl+F7\tMeta+Down\tMeta+F7,Ctrl+F7\tMeta+F7,"
     "Toggle Present Windows (Window class)"),
    ("Window Quick Tile Left",
     "Meta+Ctrl+Left,Meta+Left,Quick Tile Window to the Left"),
    ("Window Quick Tile Right",
     "Meta+Ctrl+Right,Meta+Right,Quick Tile Window to the Right"),
    ("Window Quick Tile Top",
     "Meta+Ctrl+Up,Meta+Up,Quick Tile Window to the Top"),
    ("Window Quick Tile Bottom",
     "Meta+Ctrl+Down,Meta+Down,Quick Tile Window to the Bottom"),
]

_ENSURE_FOUR_DESKTOPS = (
    'n=$(qdbus6 org.kde.KWin /VirtualDesktopManager count); '
    'for ((i=n; i<4; i++)); do '
    'qdbus6 org.kde.KWin /VirtualDesktopManager createDesktop $i '
    '"Desktop $((i+1))"; done'
)


def _spaces_step(system, plan):
    commands = [["bash", "-c", _ENSURE_FOUR_DESKTOPS]]
    for action, entry in SPACES_BINDINGS:
        commands += _binding_cmds("kwin", ["kwin"], action, entry)
    return Step(
        id="spaces",
        description="Spaces & Mission Control: 4 virtual desktops, ⌃←/→ "
                    "switching, ⌃↑ Overview, ⌃↓ App Exposé "
                    "(quick-tile moves to physical Ctrl+Alt+arrows)",
        commands=commands,
    )


# Minimal KXmlGui override: Konsole merges ActionProperties over its own UI
# file, and only enables Copy while text is selected, so Ctrl+C with no
# selection still reaches the shell as SIGINT.
KONSOLE_SESSIONUI = """\
<?xml version='1.0'?>
<!DOCTYPE gui SYSTEM 'kpartgui.dtd'>
<gui name="session" version="36">
 <ActionProperties>
  <Action name="edit_copy" shortcut="Ctrl+C"/>
  <Action name="edit_paste" shortcut="Ctrl+V"/>
 </ActionProperties>
</gui>
"""


def _appconv_step(system, plan):
    if system.konsole_sessionui_exists:
        plan.warnings.append(
            "Konsole already has a customized sessionui.rc — left untouched. "
            "Add the ⌘C/⌘V ActionProperties override by hand if wanted.")
        return None
    return Step(
        id="konsole-copy-paste",
        description="Rebind Konsole Copy/Paste to Ctrl+C/Ctrl+V "
                    "(selection-aware; Ctrl-C still interrupts)",
        file_path=f"{system.home}/.local/share/kxmlgui5/konsole/sessionui.rc",
        file_content=KONSOLE_SESSIONUI,
    )


def _clear_cmds(component, groups, key, entry):
    """Persist a cleared binding and clear it live (count 1, keycode 0)."""
    kwrite = ["kwriteconfig6", "--file", "kglobalshortcutsrc"]
    for group in groups:
        kwrite += ["--group", group]
    kwrite += ["--key", key, entry]
    bus = _BUSCTL + [component, key, "", "", "1", "0"]
    return [kwrite, bus]


# Plasma defaults that sit on Meta+Alt chords and would block Cupertino
# Rectangle's shortcut registration ([kwin] entries are 3-field).
RECTANGLE_CONFLICT_CLEARS = [
    ("kwin", ["kwin"], "Switch Window Left",
     "none,Meta+Alt+Left,Switch to Window to the Left"),
    ("kwin", ["kwin"], "Switch Window Right",
     "none,Meta+Alt+Right,Switch to Window to the Right"),
    ("kwin", ["kwin"], "Switch Window Up",
     "none,Meta+Alt+Up,Switch to Window Above"),
    ("kwin", ["kwin"], "Switch Window Down",
     "none,Meta+Alt+Down,Switch to Window Below"),
    ("KDE Keyboard Layout Switcher", ["KDE Keyboard Layout Switcher"],
     "Switch to Next Keyboard Layout",
     "none,Meta+Alt+K,Switch to Next Keyboard Layout"),
    ("org.kde.spectacle.desktop", ["services", "org.kde.spectacle.desktop"],
     "RecordScreen", "none"),
]


def _rectangle_step(system, plan):
    scripts_dir = f"{system.home}/.local/share/kwin/scripts"
    commands = [
        ["mkdir", "-p", scripts_dir],
        ["cp", "-r", f"{system.repo_root}/kwin-scripts/cupertino-snap",
         f"{scripts_dir}/"],
    ]
    for component, groups, key, entry in RECTANGLE_CONFLICT_CLEARS:
        commands += _clear_cmds(component, groups, key, entry)
    commands += [
        ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins",
         "--key", "cupertino-snapEnabled", "true"],
        ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
    ]
    return Step(
        id="rectangle",
        description="Cupertino Snap: all 22 Rectangle.app-compatible shortcuts on "
                    "physical Ctrl+Super (clears Plasma's Meta+Alt defaults "
                    "that would block them)",
        commands=commands,
    )


# The menu bar and dock ship as a Plasma Global Theme (look-and-feel/), so
# switching to another theme — and back — goes through System Settings
# instead of fighting a panel the installer built by hand. Applying with
# --resetLayout replaces every panel, so the current panel config and theme
# name are backed up first; uninstall restores them. The backup is taken only
# once, so a reinstall never overwrites the pre-kupertino layout with
# kupertino's own.
THEME_ID = "io.github.beansnr1ce.kupertino"
PANEL_FILES = ["plasma-org.kde.plasma.desktop-appletsrc", "plasmashellrc"]

_BACKUP_LAYOUT = (
    'before="$1/before"; config="$2"; shift 2; '
    '[ -e "$before" ] && exit 0; '
    'mkdir -p "$before" || exit 1; '
    'for f in "$@"; do '
    '[ -e "$config/$f" ] && { cp "$config/$f" "$before/" || exit 1; }; done; '
    'kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage '
    '> "$before/lookandfeel"'
)


def _theme_dir(system):
    return f"{system.home}/.local/share/plasma/look-and-feel"


def _state_dir(system):
    return f"{system.home}/.local/state/kupertino"


def _theme_step(system, plan):
    return Step(
        id="theme",
        description="Install and apply the Kupertino Global Theme (Breeze "
                    "Dark, menu bar, dock). Replaces your current panels — "
                    "they are backed up first and ./uninstall.sh puts them "
                    "back",
        commands=[
            ["mkdir", "-p", _theme_dir(system)],
            ["cp", "-r", f"{system.repo_root}/look-and-feel/{THEME_ID}",
             f"{_theme_dir(system)}/"],
            ["bash", "-c", _BACKUP_LAYOUT, "kupertino", _state_dir(system),
             f"{system.home}/.config"] + PANEL_FILES,
            ["plasma-apply-lookandfeel", "-a", THEME_ID, "--resetLayout"],
        ],
    )


KDE_STEP_BUILDERS = {
    "cmdq": _cmdq_step,
    "rectangle": _rectangle_step,
    "screenshots": _screenshots_step,
    "spaces": _spaces_step,
    "appconv": _appconv_step,
    "theme": _theme_step,
}


METATAP_BINDING = ("plasmashell", ["plasmashell"],
                   "activate application launcher",
                   "Alt+F1,Meta\tAlt+F1,Activate Application Launcher")


def build_plan(selections, system):
    """Turn selected feature ids + detected system state into ordered steps."""
    selected = list(selections)
    plan = Plan()

    needed = []
    for feature in selected:
        for pkg in FEATURE_PACKAGES.get(feature, []):
            if pkg not in system.installed_packages and pkg not in needed:
                needed.append(pkg)
    for pkg in needed:
        if system.package_manager not in PACKAGE_INSTALL:
            plan.warnings.append(
                f"kupertino v1.0 installs packages on CachyOS/Arch (pacman) "
                f"only — install '{pkg}' yourself before the affected steps "
                "run, or they will fail cleanly.")
            continue
        plan.steps.append(Step(
            id=f"pkg:{pkg}",
            description=f"Install package '{pkg}' ({system.package_manager})",
            commands=[PACKAGE_INSTALL[system.package_manager] + [pkg]],
        ))

    staged = f"{system.staging_dir}/default.conf"
    plan.steps.append(Step(
        id="keyd-config",
        description="Install the keyd keyboard layer to /etc/keyd/default.conf "
                    "(validated with `keyd check` first; never `keyd reload`)",
        file_path=staged,
        file_content=render_keyd_config(selected),
        commands=[
            ["keyd", "check", staged],
            ["sudo", "cp", staged, "/etc/keyd/default.conf"],
            ["sudo", "systemctl", "enable", "--now", "keyd"],
            ["sudo", "systemctl", "restart", "keyd"],
        ],
    ))

    # Physical Ctrl emits Meta, so every bare Ctrl tap — crouch in a game,
    # a released chord — fires KDE's Meta-tap binding and Kickoff covers the
    # screen. macOS has no such behavior, so this is unconditional rather than
    # a feature. Two *independent* bindings put Kickoff on a bare Meta tap and
    # both have to go (2026-08-22: clearing only the first left it firing):
    # KWin's modifier-only shortcut, and plasmashell's real global shortcut on
    # bare Meta, which is the one that actually fires. Kickoff stays reachable
    # on Alt+F1 (physical Win+F1) and from any launcher widget on a panel.
    plan.steps.append(Step(
        id="metatap",
        description="Stop a bare physical-Ctrl tap from opening the "
                    "application launcher (no macOS equivalent; Kickoff "
                    "stays on Alt+F1)",
        commands=(
            [["kwriteconfig6", "--file", "kwinrc",
              "--group", "ModifierOnlyShortcuts", "--key", "Meta", ""]]
            + _binding_cmds(*METATAP_BINDING)
            + [["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"]]
        ),
    ))

    for feature in selected:
        builder = KDE_STEP_BUILDERS.get(feature)
        if builder is None:
            continue
        step = builder(system, plan)
        if step is not None:
            plan.steps.append(step)
    return plan


# --- uninstall --------------------------------------------------------------
# Stateless on purpose: installs from before uninstall existed kept no record,
# so uninstall reads the live config and reverts only what still carries
# kupertino's exact value. Anything the user has changed since is left alone.

@dataclass
class InstalledState:
    home: str
    keyd_config: str        # /etc/keyd/default.conf, "" if absent
    kglobalshortcuts: dict  # parse_kconfig() of kglobalshortcutsrc
    kwinrc: dict            # parse_kconfig() of kwinrc
    konsole_sessionui: str  # "" if absent
    snap_installed: bool
    theme_installed: bool
    active_theme: str
    previous_theme: str     # from the install-time backup, "" if none
    panels_backed_up: bool


_KCONFIG_ESCAPES = {"\\\\": "\\", "\\t": "\t", "\\n": "\n", "\\r": "\r",
                    "\\s": " "}


def parse_kconfig(text):
    """{(groups, key): value} for a KConfig file, with escapes decoded.

    groups is a tuple, e.g. ('services', 'org.kde.spectacle.desktop').
    kglobalshortcutsrc stores the tab between sequences as a literal \\t.
    """
    entries = {}
    groups = ()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            groups = tuple(line[1:-1].split("]["))
        elif "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            entries[(groups, key)] = re.sub(
                r"\\[\\tnrs]", lambda m: _KCONFIG_ESCAPES[m.group()], value)
    return entries


# Every (component, groups, key, entry) the installer can write.
KUPERTINO_BINDINGS = (
    [CMDQ_BINDING, METATAP_BINDING]
    + [("kwin", ["kwin"], action, entry) for action, entry in SPACES_BINDINGS]
    + [("org.kde.spectacle.desktop", ["services", "org.kde.spectacle.desktop"],
        action, entry) for action, entry in SPECTACLE_BINDINGS]
    + RECTANGLE_CONFLICT_CLEARS
)


def stock_entry(groups, key, entry):
    """Plasma's default for a binding kupertino wrote.

    [kwin]-style entries carry their default as the second field; [services]
    entries hold only the active field, so those defaults are tabled.
    """
    if groups[0] == "services":
        return SPECTACLE_DEFAULTS[key]
    _active, default, description = entry.split(",")
    return f"{default},{default},{description}"


# Only kupertino's config has the physical-Alt-as-Command layer.
KEYD_SIGNATURE = "leftalt = layer(cmd)"

# With no config left keyd has nothing to do, so it is stopped rather than
# restarted — unless the user has other configs of their own.
_STOP_KEYD = (
    "if ls /etc/keyd/*.conf >/dev/null 2>&1; "
    "then sudo systemctl restart keyd; "
    "else sudo systemctl disable --now keyd; fi"
)

# plasmashell rewrites its panel config on exit, so it must be stopped while
# the backup goes back in — and started again even if the copy fails.
_RESTORE_PANELS = (
    "systemctl --user stop plasma-plasmashell.service; "
    'cp "$1"/*rc "$2/"; rc=$?; '
    "systemctl --user start plasma-plasmashell.service; exit $rc"
)


def build_uninstall_plan(installed):
    """Turn what is still installed into ordered revert steps."""
    plan = Plan()
    home = installed.home
    state = f"{home}/.local/state/kupertino"

    if installed.active_theme == THEME_ID:
        previous = installed.previous_theme or "org.kde.breeze.desktop"
        if installed.panels_backed_up:
            plan.steps.append(Step(
                id="theme-restore",
                description=f"Switch back to your previous Global Theme "
                            f"({previous}) and restore the panels you had "
                            "before kupertino",
                commands=[
                    ["plasma-apply-lookandfeel", "-a", previous],
                    ["bash", "-c", _RESTORE_PANELS, "kupertino",
                     f"{state}/before", f"{home}/.config"],
                ],
            ))
        else:
            plan.steps.append(Step(
                id="theme-restore",
                description=f"Switch to the {previous} Global Theme with its "
                            "default panels (no pre-kupertino panel backup "
                            "was found)",
                commands=[["plasma-apply-lookandfeel", "-a", previous,
                           "--resetLayout"]],
            ))
    elif installed.theme_installed:
        plan.warnings.append(
            "Kupertino isn't your active Global Theme, so your current look "
            "and panels are left as they are.")

    if installed.theme_installed or installed.panels_backed_up:
        plan.steps.append(Step(
            id="theme-remove",
            description="Remove the Kupertino Global Theme package and its "
                        "panel backup",
            commands=[["rm", "-rf",
                       f"{home}/.local/share/plasma/look-and-feel/{THEME_ID}",
                       state]],
        ))

    # Before the shortcut reset: the script holds the Meta+Alt chords that
    # Plasma's restored defaults need back.
    snap_enabled = installed.kwinrc.get(
        (("Plugins",), "cupertino-snapEnabled")) == "true"
    if installed.snap_installed or snap_enabled:
        plan.steps.append(Step(
            id="snap",
            description="Disable and remove the Cupertino Snap KWin script",
            commands=[
                ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins",
                 "--key", "cupertino-snapEnabled", "--delete"],
                ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
                ["rm", "-rf", f"{home}/.local/share/kwin/scripts/cupertino-snap"],
            ],
        ))

    commands = []
    for component, groups, key, entry in KUPERTINO_BINDINGS:
        if installed.kglobalshortcuts.get((tuple(groups), key)) == entry:
            commands += _binding_cmds(component, groups, key,
                                      stock_entry(groups, key, entry))
    if installed.kwinrc.get((("ModifierOnlyShortcuts",), "Meta")) == "":
        commands.append(["kwriteconfig6", "--file", "kwinrc",
                         "--group", "ModifierOnlyShortcuts", "--key", "Meta",
                         "--delete"])
    if commands:
        plan.steps.append(Step(
            id="shortcuts",
            description="Reset the KDE shortcuts kupertino changed to Plasma's "
                        "defaults (any you've changed since are left alone)",
            commands=commands + [["qdbus6", "org.kde.KWin", "/KWin",
                                  "reconfigure"]],
        ))

    if installed.konsole_sessionui == KONSOLE_SESSIONUI:
        plan.steps.append(Step(
            id="konsole-copy-paste",
            description="Remove kupertino's Konsole Copy/Paste override",
            commands=[["rm", f"{home}/.local/share/kxmlgui5/konsole/"
                             "sessionui.rc"]],
        ))

    if KEYD_SIGNATURE in installed.keyd_config:
        plan.steps.append(Step(
            id="keyd-config",
            description="Remove the keyd keyboard layer "
                        "(/etc/keyd/default.conf); the modifier row is back "
                        "to normal immediately",
            commands=[["sudo", "rm", "/etc/keyd/default.conf"],
                      ["bash", "-c", _STOP_KEYD]],
        ))

    plan.warnings.append(
        "Left in place: installed packages (keyd, spectacle, "
        "appmenu-gtk-module) and your virtual desktops.")
    return plan


# --- imperative shell (untested; verified by hand) --------------------------

def detect_system():
    import shutil
    import tempfile
    from pathlib import Path

    home = str(Path.home())
    manager = next(
        (m for m in ("pacman", "apt", "dnf", "zypper") if shutil.which(m)),
        None)
    installed = {p for p in ("keyd", "spectacle") if shutil.which(p)}
    # appmenu-gtk-module ships no binary, so which() can't see it.
    if Path("/usr/lib/gtk-3.0/modules/libappmenu-gtk-module.so").exists():
        installed.add("appmenu-gtk-module")
    sessionui = Path(home) / ".local/share/kxmlgui5/konsole/sessionui.rc"
    return SystemState(
        package_manager=manager,
        installed_packages=installed,
        staging_dir=tempfile.mkdtemp(prefix="kupertino-"),
        home=home,
        repo_root=str(Path(__file__).resolve().parent),
        konsole_sessionui_exists=sessionui.exists(),
    )


def detect_installed():
    from pathlib import Path

    home = Path.home()

    def read(path):
        try:
            return Path(path).read_text()
        except OSError:
            return ""

    before = home / ".local/state/kupertino/before"
    kdeglobals = parse_kconfig(read(home / ".config/kdeglobals"))
    return InstalledState(
        home=str(home),
        keyd_config=read("/etc/keyd/default.conf"),
        kglobalshortcuts=parse_kconfig(read(home / ".config/kglobalshortcutsrc")),
        kwinrc=parse_kconfig(read(home / ".config/kwinrc")),
        konsole_sessionui=read(
            home / ".local/share/kxmlgui5/konsole/sessionui.rc"),
        snap_installed=(home / ".local/share/kwin/scripts/cupertino-snap").exists(),
        theme_installed=(home / ".local/share/plasma/look-and-feel"
                         / THEME_ID).exists(),
        active_theme=kdeglobals.get((("KDE",), "LookAndFeelPackage"), ""),
        previous_theme=read(before / "lookandfeel").strip(),
        panels_backed_up=(before / PANEL_FILES[0]).exists(),
    )


def _authorize_and_run(plan, verb, script, say, ask):
    """Shared tail of install and uninstall: warn, authorize, execute."""
    import subprocess
    from pathlib import Path

    for warning in plan.warnings:
        say(f"\n⚠ {warning}")
    if not plan.steps:
        say(f"\nNothing to {verb} — no changes made.")
        return 0

    say(f"\n{len(plan.steps)} step(s) to {verb}. Authorize each:")
    approved = authorize_plan(plan, ask, say)
    if not approved:
        say("\nNothing authorized — no changes made.")
        return 0

    def write_file(path, content):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)

    say("")
    result = execute(approved, subprocess.call, write_file, say)
    if result.failed:
        say(f"\n✗ Step '{result.failed}' failed — remaining steps were NOT "
            f"run. Fix the error and re-run {script} (steps are "
            "idempotent).")
        return 1
    say(f"\n✓ Done — {len(result.completed)} step(s) completed. Changes "
        "are live now; no logout needed.")
    return 0


def main(argv=None):
    import sys

    argv = sys.argv[1:] if argv is None else argv
    say, ask = print, input

    if argv == ["--uninstall"]:
        say("kupertino — uninstall")
        say("=" * 21)
        say("Reverts only what still carries kupertino's values; anything")
        say("you've changed since is left alone. Authorize each step.")
        return _authorize_and_run(build_uninstall_plan(detect_installed()),
                                  "uninstall", "./uninstall.sh", say, ask)

    say("kupertino — macOS keyboard shortcuts for KDE Plasma")
    say("=" * 51)
    say("Pick features first; nothing is installed until you authorize each")
    say("step at the end. keyd's panic exit, should a config ever lock your")
    say("keyboard, is Backspace+Escape+Enter.")

    selections = run_wizard(FEATURES, ask, say)
    if not selections:
        say("\nNothing selected — no changes made.")
        return 0

    return _authorize_and_run(build_plan(selections, detect_system()),
                              "install", "./install.sh", say, ask)


def render_keyd_config(selections):
    """Assemble /etc/keyd/default.conf from the selected features' fragments."""
    selected = set(selections)
    blocks = []
    for section in KEYD_SECTIONS:
        gate = section.get("feature")
        if gate is not None and gate not in selected:
            continue
        lines = list(section["header"])
        for feature, line in section["entries"]:
            if feature is None or feature in selected:
                lines.append(line)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"

if __name__ == "__main__":
    raise SystemExit(main())
