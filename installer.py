#!/usr/bin/env python3
"""kupertino interactive installer.

Walks through each shortcut feature, then installs the user's selections,
asking authorization for every step. Stdlib only; tests in tests/.
"""

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
    Feature("rectangle", "Rectangle window management",
            "All 22 Rectangle.app shortcuts on ⌃⌥ (physical Ctrl+Super): "
            "halves, corners, thirds, maximize, center, restore, displays."),
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
}

PACKAGE_INSTALL = {
    "pacman": ["sudo", "pacman", "-S", "--needed"],
    "apt": ["sudo", "apt", "install"],
    "dnf": ["sudo", "dnf", "install"],
    "zypper": ["sudo", "zypper", "install"],
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


def _cmdq_step(system, plan):
    return Step(
        id="cmdq",
        description="Bind KDE-side Ctrl+Q (physical Alt+Q, mac ⌘Q) to KWin's "
                    "Window Close",
        commands=_binding_cmds("kwin", ["kwin"], "Window Close",
                               "Ctrl+Q\tAlt+F4,Alt+F4,Close Window"),
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
        ["cp", "-r", f"{system.repo_root}/kwin-scripts/cupertino-rectangle",
         f"{scripts_dir}/"],
    ]
    for component, groups, key, entry in RECTANGLE_CONFLICT_CLEARS:
        commands += _clear_cmds(component, groups, key, entry)
    commands += [
        ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins",
         "--key", "cupertino-rectangleEnabled", "true"],
        ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
    ]
    return Step(
        id="rectangle",
        description="Cupertino Rectangle: all 22 Rectangle.app shortcuts on "
                    "physical Ctrl+Super (clears Plasma's Meta+Alt defaults "
                    "that would block them)",
        commands=commands,
    )


KDE_STEP_BUILDERS = {
    "cmdq": _cmdq_step,
    "rectangle": _rectangle_step,
    "screenshots": _screenshots_step,
    "spaces": _spaces_step,
    "appconv": _appconv_step,
}


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
                f"No supported package manager found — install '{pkg}' "
                "yourself before running the affected steps.")
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

    for feature in selected:
        builder = KDE_STEP_BUILDERS.get(feature)
        if builder is None:
            continue
        step = builder(system, plan)
        if step is not None:
            plan.steps.append(step)
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
    sessionui = Path(home) / ".local/share/kxmlgui5/konsole/sessionui.rc"
    return SystemState(
        package_manager=manager,
        installed_packages=installed,
        staging_dir=tempfile.mkdtemp(prefix="kupertino-"),
        home=home,
        repo_root=str(Path(__file__).resolve().parent),
        konsole_sessionui_exists=sessionui.exists(),
    )


def main():
    import subprocess
    from pathlib import Path

    say, ask = print, input
    say("kupertino — macOS keyboard shortcuts for KDE Plasma")
    say("=" * 51)
    say("Pick features first; nothing is installed until you authorize each")
    say("step at the end. keyd's panic exit, should a config ever lock your")
    say("keyboard, is Backspace+Escape+Enter.")

    selections = run_wizard(FEATURES, ask, say)
    if not selections:
        say("\nNothing selected — no changes made.")
        return 0

    plan = build_plan(selections, detect_system())
    for warning in plan.warnings:
        say(f"\n⚠ {warning}")

    say(f"\n{len(plan.steps)} step(s) to install. Authorize each:")
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
            "run. Fix the error and re-run ./install.sh (steps are "
            "idempotent).")
        return 1
    say(f"\n✓ Done — {len(result.completed)} step(s) installed. Shortcuts "
        "are live now; no logout needed.")
    return 0


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
