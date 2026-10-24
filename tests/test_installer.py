"""Tests for the kupertino interactive installer.

Seams under test (agreed 2026-08-20):
  S1 render_keyd_config(selections)   - pure: assembles /etc/keyd/default.conf
  S2 build_plan(selections, system)   - pure: selections -> ordered install steps
  S3 run_wizard(...)                  - interactive walk, scripted IO
  S4 authorize_plan(...)              - per-step authorization, scripted IO
  S5 execute(...)                     - runs a plan through injected runners
  S6 build_uninstall_plan(installed)  - pure: live config -> ordered revert steps

Real package installs, sudo, and D-Bus stay untested imperative shell.
Expected values come from the reference machine's known-good configs,
not from re-running the implementation's logic.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import installer


class TestRenderKeydConfig(unittest.TestCase):
    def test_remap_only_renders_base_layers(self):
        # Hand-derived from the reference /etc/keyd/default.conf: just the
        # modifier-row remap, no per-feature entries in the cmd/opt layers.
        expected = """\
[ids]
*

[main]
leftalt = layer(cmd)
leftmeta = layer(opt)
leftcontrol = layer(meta)

# Physical Alt = macOS Command (acts as Ctrl, plus mac text navigation)
[cmd:C]

# Physical Win = macOS Option (acts as Alt, plus word-wise movement)
[opt:A]
"""
        self.assertEqual(installer.render_keyd_config(["remap"]), expected)

    def test_all_features_reproduce_reference_config(self):
        # keyd/default.conf is the working config from the reference machine —
        # the independent source of truth the assembly must reproduce exactly.
        reference = (REPO / "keyd" / "default.conf").read_text()
        rendered = installer.render_keyd_config(
            ["remap", "textnav", "cmdtab", "cmdq", "screenshots",
             "spaces", "appconv", "rectangle"]
        )
        self.assertEqual(rendered, reference)

    def test_textnav_subset_renders_only_text_entries(self):
        expected = """\
[ids]
*

[main]
leftalt = layer(cmd)
leftmeta = layer(opt)
leftcontrol = layer(meta)

# Physical Alt = macOS Command (acts as Ctrl, plus mac text navigation)
[cmd:C]
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
"""
        self.assertEqual(
            installer.render_keyd_config(["remap", "textnav"]), expected
        )


class TestQtKeycode(unittest.TestCase):
    def test_worked_examples_from_reference_doc(self):
        # Values verified live on the reference machine (docs/kupertino-layer.md):
        # arrows carry 0x01000000 and run Left, Up, Right, Down.
        cases = {
            "Ctrl+Space": 67108896,
            "Alt+Space": 134217760,
            "Alt+F4": 150994995,
            "Ctrl+Q": 67108945,
            "Meta+Ctrl+Left": 0x15000012,
            "Meta+Up": 0x11000013,
            "Ctrl+Shift+3": 100663347,
            "Ctrl+#": 67108899,
            "Shift+Print": 0x03000009,
            "Meta+Shift+S": 0x12000053,
        }
        for seq, code in cases.items():
            with self.subTest(seq=seq):
                self.assertEqual(installer.qt_keycode(seq), code)


def make_system(**kw):
    defaults = dict(
        package_manager="pacman",
        installed_packages=set(),
        staging_dir="/stage",
        home="/home/u",
        repo_root="/repo",
        konsole_sessionui_exists=False,
    )
    defaults.update(kw)
    return installer.SystemState(**defaults)


class TestBuildPlan(unittest.TestCase):
    def test_remap_plan_installs_keyd_then_config(self):
        plan = installer.build_plan(["remap"], make_system())
        self.assertEqual([s.id for s in plan.steps],
                         ["pkg:keyd", "keyd-config", "metatap"])

        # Non-interactive on purpose: the user already authorized this exact
        # step, and an interactive prompt deadlocks when stdin is piped
        # (found in the 2026-08-20 container smoke tests).
        pkg = plan.steps[0]
        self.assertEqual(
            pkg.commands,
            [["sudo", "pacman", "-S", "--needed", "--noconfirm", "keyd"]],
        )

        cfg = plan.steps[1]
        self.assertEqual(cfg.file_path, "/stage/default.conf")
        self.assertIn("leftcontrol = layer(meta)", cfg.file_content)
        self.assertNotIn("[meta+opt]", cfg.file_content)
        self.assertEqual(
            cfg.commands,
            [
                ["keyd", "check", "/stage/default.conf"],
                ["sudo", "cp", "/stage/default.conf", "/etc/keyd/default.conf"],
                ["sudo", "systemctl", "enable", "--now", "keyd"],
                ["sudo", "systemctl", "restart", "keyd"],
            ],
        )


BUSCTL = ["busctl", "--user", "call", "org.kde.kglobalaccel", "/kglobalaccel",
          "org.kde.KGlobalAccel", "setForeignShortcut", "asai", "4"]


class TestBuildPlanKdeSteps(unittest.TestCase):
    def test_cmdq_and_screenshots_steps_with_deps_installed(self):
        system = make_system(installed_packages={"keyd", "spectacle"})
        plan = installer.build_plan(["remap", "cmdq", "screenshots"], system)
        self.assertEqual(
            [s.id for s in plan.steps],
            ["keyd-config", "metatap", "cmdq", "screenshots"],
        )

        # Entries below are transcribed from the reference machine's working
        # kglobalshortcutsrc ([kwin] entries are active,default,description).
        cmdq = plan.steps[2]
        self.assertEqual(cmdq.commands, [
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "kwin", "--key", "Window Close",
             "Ctrl+Q\tAlt+F4,Alt+F4,Close Window"],
            BUSCTL + ["kwin", "Window Close", "", "", "2",
                      "67108945", "150994995"],
        ])

        shots = plan.steps[3]
        self.assertIn(
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "services", "--group", "org.kde.spectacle.desktop",
             "--key", "FullScreenScreenShot",
             "Shift+Print\tCtrl+#\tCtrl+Shift+#\tCtrl+Shift+3"],
            shots.commands,
        )
        self.assertIn(
            BUSCTL + ["org.kde.spectacle.desktop", "FullScreenScreenShot",
                      "", "", "4",
                      "50331657", "67108899", "100663331", "100663347"],
            shots.commands,
        )

    def test_non_pacman_manager_warns_and_skips_package_steps(self):
        # v1.0 targets CachyOS/Arch (pacman). Elsewhere: warn, skip package
        # installs, still proceed with the config steps. (2026-08-20 container
        # smoke tests: Ubuntu 24.04 has no keyd package at all, Fedora needs a
        # COPR — supporting those properly is future work.)
        system = make_system(package_manager="apt", installed_packages={"keyd"})
        plan = installer.build_plan(["remap", "screenshots"], system)
        self.assertNotIn("pkg:spectacle", [s.id for s in plan.steps])
        self.assertTrue(any("spectacle" in w for w in plan.warnings))
        self.assertIn("keyd-config", [s.id for s in plan.steps])

    def test_unknown_package_manager_warns_instead_of_crashing(self):
        system = make_system(package_manager=None)
        plan = installer.build_plan(["remap"], system)
        self.assertEqual([s.id for s in plan.steps],
                         ["keyd-config", "metatap"])
        self.assertTrue(any("keyd" in w for w in plan.warnings))

    def test_metatap_step_kills_both_launcher_bindings(self):
        # Physical Ctrl emits Meta, so a bare Ctrl tap (crouch in a game)
        # opened Kickoff. Two independent bindings do that; clearing only
        # KWin's modifier-only shortcut left it firing (2026-08-22), so both
        # must be in the step. Unconditional: it has no macOS equivalent.
        plan = installer.build_plan(["remap"],
                                    make_system(installed_packages={"keyd"}))
        step = next(s for s in plan.steps if s.id == "metatap")
        self.assertEqual(step.commands, [
            ["kwriteconfig6", "--file", "kwinrc",
             "--group", "ModifierOnlyShortcuts", "--key", "Meta", ""],
            # Active field keeps Alt+F1 only; Meta stays in the default field
            # so KDE's "reset to default" still restores stock behavior.
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "plasmashell", "--key", "activate application launcher",
             "Alt+F1,Meta\tAlt+F1,Activate Application Launcher"],
            BUSCTL + ["plasmashell", "activate application launcher",
                      "", "", "1", "150994992"],  # Alt+F1 = 0x09000030
            ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
        ])

    def test_spaces_step_creates_desktops_and_bindings(self):
        plan = installer.build_plan(
            ["remap", "spaces"], make_system(installed_packages={"keyd"})
        )
        spaces = plan.steps[-1]
        self.assertEqual(spaces.id, "spaces")
        self.assertEqual(
            spaces.commands[0],
            ["bash", "-c",
             'n=$(qdbus6 org.kde.KWin /VirtualDesktopManager count); '
             'for ((i=n; i<4; i++)); do '
             'qdbus6 org.kde.KWin /VirtualDesktopManager createDesktop $i '
             '"Desktop $((i+1))"; done'],
        )
        self.assertIn(
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "kwin", "--key", "Switch One Desktop to the Left",
             "Meta+Left,Meta+Ctrl+Left,Switch One Desktop to the Left"],
            spaces.commands,
        )
        self.assertIn(
            BUSCTL + ["kwin", "Switch One Desktop to the Left", "", "", "1",
                      "285212690"],
            spaces.commands,
        )
        # Quick-tile moves to Meta+Ctrl+arrows (0x15000012 for Left)
        self.assertIn(
            BUSCTL + ["kwin", "Window Quick Tile Left", "", "", "1",
                      "352321554"],
            spaces.commands,
        )

    def test_appconv_writes_konsole_override(self):
        plan = installer.build_plan(
            ["remap", "appconv"], make_system(installed_packages={"keyd"})
        )
        konsole = plan.steps[-1]
        self.assertEqual(konsole.id, "konsole-copy-paste")
        self.assertEqual(
            konsole.file_path,
            "/home/u/.local/share/kxmlgui5/konsole/sessionui.rc",
        )
        self.assertIn('<Action name="edit_copy" shortcut="Ctrl+C"/>',
                      konsole.file_content)
        self.assertIn('<Action name="edit_paste" shortcut="Ctrl+V"/>',
                      konsole.file_content)
        self.assertEqual(konsole.commands, [])

    def test_appconv_never_clobbers_existing_konsole_override(self):
        plan = installer.build_plan(
            ["remap", "appconv"],
            make_system(installed_packages={"keyd"},
                        konsole_sessionui_exists=True),
        )
        self.assertNotIn("konsole-copy-paste", [s.id for s in plan.steps])
        self.assertTrue(any("sessionui.rc" in w for w in plan.warnings))

    def test_rectangle_step_installs_script_and_clears_conflicts(self):
        plan = installer.build_plan(
            ["remap", "rectangle"], make_system(installed_packages={"keyd"})
        )
        rect = plan.steps[-1]
        self.assertEqual(rect.id, "rectangle")
        self.assertEqual(
            rect.commands[0],
            ["mkdir", "-p", "/home/u/.local/share/kwin/scripts"],
        )
        self.assertEqual(
            rect.commands[1],
            ["cp", "-r", "/repo/kwin-scripts/cupertino-snap",
             "/home/u/.local/share/kwin/scripts/"],
        )
        # Plasma defaults on Meta+Alt block the script's shortcut registration
        self.assertIn(
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "kwin", "--key", "Switch Window Left",
             "none,Meta+Alt+Left,Switch to Window to the Left"],
            rect.commands,
        )
        self.assertIn(
            BUSCTL + ["kwin", "Switch Window Left", "", "", "1", "0"],
            rect.commands,
        )
        self.assertIn(
            BUSCTL + ["KDE Keyboard Layout Switcher",
                      "Switch to Next Keyboard Layout", "", "", "1", "0"],
            rect.commands,
        )
        self.assertEqual(
            rect.commands[-2:],
            [["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins",
              "--key", "cupertino-snapEnabled", "true"],
             ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"]],
        )


LAYOUT = (REPO / "look-and-feel" / installer.THEME_ID / "contents" / "layouts"
          / "org.kde.plasma.desktop-layout.js")


class TestThemeLayout(unittest.TestCase):
    """The menu bar lives in the Global Theme's layout script."""

    def setUp(self):
        self.script = LAYOUT.read_text()

    def test_menu_bar_widgets_in_mac_order(self):
        # addWidget() appends and Plasma has no reorder API, so the order
        # these calls appear in *is* the resulting panel order.
        positions = [
            self.script.index('menubar.addWidget("org.kde.plasma.appmenu")'),
            self.script.index('menubar.addWidget("org.kde.plasma.panelspacer")'),
            self.script.index('menubar.addWidget("org.kde.plasma.systemtray")'),
            self.script.index('menubar.addWidget("org.kde.plasma.digitalclock")'),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_spacer_is_expanding(self):
        # Load-bearing: the Global Menu applet declares CanFillArea, so
        # without an expanding spacer it is the panel's only stretching
        # element and the tray slides left whenever an app (Steam, Electron)
        # exports no menu.
        self.assertIn('spacer.currentConfigGroup = ["General"];', self.script)
        self.assertIn('spacer.writeConfig("expanding", true);', self.script)

    def test_menu_bar_is_flush_and_full_width(self):
        for setting in ('menubar.location = "top";',
                        'menubar.floating = false;',
                        'menubar.lengthMode = "fill";',
                        'menubar.hiding = "none";'):
            self.assertIn(setting, self.script)

    def test_dock_keeps_a_launcher(self):
        # kupertino clears the bare-Meta tap, so the dock's Kickoff is the
        # launcher's only mouse entry point.
        self.assertIn('dock.location = "bottom";', self.script)
        self.assertIn('dock.addWidget("org.kde.plasma.kickoff")', self.script)


class TestThemeStep(unittest.TestCase):
    def _plan(self):
        return installer.build_plan(
            ["remap", "theme"],
            make_system(installed_packages={"keyd", "appmenu-gtk-module"}),
        )

    def test_theme_alone_does_not_disturb_keyd_config(self):
        self.assertEqual([s.id for s in self._plan().steps],
                         ["keyd-config", "metatap", "theme"])

    def test_installs_backs_up_then_applies_with_layout(self):
        theme = self._plan().steps[-1]
        self.assertEqual(theme.commands[0],
                         ["mkdir", "-p", "/home/u/.local/share/plasma/look-and-feel"])
        self.assertEqual(
            theme.commands[1],
            ["cp", "-r", "/repo/look-and-feel/io.github.beansnr1ce.kupertino",
             "/home/u/.local/share/plasma/look-and-feel/"])
        backup = theme.commands[2]
        self.assertEqual(backup[:2], ["bash", "-c"])
        self.assertEqual(backup[3:], [
            "kupertino", "/home/u/.local/state/kupertino", "/home/u/.config",
            "plasma-org.kde.plasma.desktop-appletsrc", "plasmashellrc"])
        # A reinstall must not overwrite the pre-kupertino backup with
        # kupertino's own layout.
        self.assertIn('[ -e "$before" ] && exit 0', backup[2])
        # --resetLayout is what replaces the panels; without it only the
        # visuals change and no menu bar appears.
        self.assertEqual(
            theme.commands[3],
            ["plasma-apply-lookandfeel", "-a", "io.github.beansnr1ce.kupertino",
             "--resetLayout"])

    def test_pulls_in_gtk_menu_export_module(self):
        # Qt/KDE apps export menus unaided; GTK apps need the module or the
        # menu bar is empty for them.
        plan = installer.build_plan(["remap", "theme"],
                                    make_system(installed_packages={"keyd"}))
        self.assertEqual(plan.steps[0].id, "pkg:appmenu-gtk-module")
        self.assertEqual(
            plan.steps[0].commands,
            [["sudo", "pacman", "-S", "--needed", "--noconfirm",
              "appmenu-gtk-module"]],
        )


class TestParseKconfig(unittest.TestCase):
    def test_reads_nested_groups_and_decodes_tabs(self):
        # Excerpt of the reference machine's kglobalshortcutsrc: the tab
        # between sequences is stored as a literal backslash-t.
        text = r"""[kwin]
Window Close=Ctrl+Q\tAlt+F4,Alt+F4,Close Window

[services][org.kde.spectacle.desktop]
RecordScreen=none
"""
        entries = installer.parse_kconfig(text)
        self.assertEqual(entries[(("kwin",), "Window Close")],
                         "Ctrl+Q\tAlt+F4,Alt+F4,Close Window")
        self.assertEqual(
            entries[(("services", "org.kde.spectacle.desktop"), "RecordScreen")],
            "none")

    def test_empty_value_is_kept(self):
        # kwinrc's cleared launcher tap is `Meta=` — present but empty.
        entries = installer.parse_kconfig("[ModifierOnlyShortcuts]\nMeta=\n")
        self.assertEqual(entries[(("ModifierOnlyShortcuts",), "Meta")], "")


# The reference machine's live config after a full install, transcribed.
REFERENCE_SHORTCUTS = r"""[KDE Keyboard Layout Switcher]
Switch to Next Keyboard Layout=none,Meta+Alt+K,Switch to Next Keyboard Layout

[kwin]
ExposeClass=Ctrl+F7\tMeta+Down\tMeta+F7,Ctrl+F7\tMeta+F7,Toggle Present Windows (Window class)
Overview=Meta+W\tMeta+Up,Meta+W,Toggle Overview
Switch One Desktop to the Left=Meta+Left,Meta+Ctrl+Left,Switch One Desktop to the Left
Switch One Desktop to the Right=Meta+Right,Meta+Ctrl+Right,Switch One Desktop to the Right
Switch Window Down=none,Meta+Alt+Down,Switch to Window Below
Switch Window Left=none,Meta+Alt+Left,Switch to Window to the Left
Switch Window Right=none,Meta+Alt+Right,Switch to Window to the Right
Switch Window Up=none,Meta+Alt+Up,Switch to Window Above
Window Close=Ctrl+Q\tAlt+F4,Alt+F4,Close Window
Window Quick Tile Bottom=Meta+Ctrl+Down,Meta+Down,Quick Tile Window to the Bottom
Window Quick Tile Left=Meta+Ctrl+Left,Meta+Left,Quick Tile Window to the Left
Window Quick Tile Right=Meta+Ctrl+Right,Meta+Right,Quick Tile Window to the Right
Window Quick Tile Top=Meta+Ctrl+Up,Meta+Up,Quick Tile Window to the Top

[plasmashell]
activate application launcher=Alt+F1,Meta\tAlt+F1,Activate Application Launcher

[services][org.kde.spectacle.desktop]
ActiveWindowScreenShot=Ctrl+^\tCtrl+Shift+6\tCtrl+Shift+^\tMeta+Print
FullScreenScreenShot=Shift+Print\tCtrl+#\tCtrl+Shift+#\tCtrl+Shift+3
RecordScreen=none
RectangularRegionScreenShot=Ctrl+$\tCtrl+Shift+$\tCtrl+Shift+4\tMeta+Shift+Print
_launch=Print\tCtrl+%\tCtrl+Shift+%\tCtrl+Shift+5\tMeta+Shift+S
"""

REFERENCE_KWINRC = """[ModifierOnlyShortcuts]
Meta=

[Plugins]
cupertino-snapEnabled=true
"""


def make_installed(**kw):
    defaults = dict(
        home="/home/u",
        keyd_config=(REPO / "keyd" / "default.conf").read_text(),
        kglobalshortcuts=installer.parse_kconfig(REFERENCE_SHORTCUTS),
        kwinrc=installer.parse_kconfig(REFERENCE_KWINRC),
        konsole_sessionui=installer.KONSOLE_SESSIONUI,
        snap_installed=True,
        theme_installed=True,
        active_theme="io.github.beansnr1ce.kupertino",
        previous_theme="org.kde.breezedark.desktop",
        panels_backed_up=True,
    )
    defaults.update(kw)
    return installer.InstalledState(**defaults)


def make_clean(**kw):
    """A machine with nothing of kupertino's on it."""
    defaults = dict(keyd_config="", kglobalshortcuts={}, kwinrc={},
                    konsole_sessionui="", snap_installed=False,
                    theme_installed=False, active_theme="org.kde.breeze.desktop",
                    previous_theme="", panels_backed_up=False)
    defaults.update(kw)
    return make_installed(**defaults)


class TestUninstallPlan(unittest.TestCase):
    def test_full_install_reverts_everything_in_order(self):
        plan = installer.build_uninstall_plan(make_installed())
        # Snap before shortcuts: the script holds the Meta+Alt chords that
        # Plasma's restored defaults need back.
        self.assertEqual(
            [s.id for s in plan.steps],
            ["theme-restore", "theme-remove", "snap", "shortcuts",
             "konsole-copy-paste", "keyd-config"])

    def test_clean_machine_has_nothing_to_do(self):
        plan = installer.build_uninstall_plan(make_clean())
        self.assertEqual(plan.steps, [])

    def test_theme_restore_puts_back_previous_theme_and_panels(self):
        plan = installer.build_uninstall_plan(make_installed())
        restore = plan.steps[0]
        self.assertEqual(restore.commands[0],
                         ["plasma-apply-lookandfeel", "-a",
                          "org.kde.breezedark.desktop"])
        script, *args = restore.commands[1][2:]
        self.assertEqual(args, ["kupertino", "/home/u/.local/state/kupertino/before",
                                "/home/u/.config"])
        # plasmashell rewrites its config on exit, so it is stopped around
        # the copy and started again even if the copy fails.
        self.assertLess(script.index("stop plasma-plasmashell"),
                        script.index("cp "))
        self.assertTrue(script.endswith(
            "start plasma-plasmashell.service; exit $rc"))

    def test_theme_restore_without_backup_resets_to_breeze_layout(self):
        plan = installer.build_uninstall_plan(
            make_installed(previous_theme="", panels_backed_up=False))
        self.assertEqual(plan.steps[0].commands,
                         [["plasma-apply-lookandfeel", "-a",
                           "org.kde.breeze.desktop", "--resetLayout"]])

    def test_another_active_theme_is_left_alone(self):
        # The whole point: trying WhiteSur after kupertino must not be undone
        # by uninstalling kupertino.
        plan = installer.build_uninstall_plan(make_installed(
            active_theme="com.github.vinceliuice.WhiteSurLiquid-dark"))
        ids = [s.id for s in plan.steps]
        self.assertNotIn("theme-restore", ids)
        self.assertIn("theme-remove", ids)
        self.assertTrue(any("isn't your active Global Theme" in w
                            for w in plan.warnings))

    def test_theme_remove_deletes_package_and_backup(self):
        plan = installer.build_uninstall_plan(make_installed())
        remove = next(s for s in plan.steps if s.id == "theme-remove")
        self.assertEqual(remove.commands, [[
            "rm", "-rf",
            "/home/u/.local/share/plasma/look-and-feel/"
            "io.github.beansnr1ce.kupertino",
            "/home/u/.local/state/kupertino"]])

    def test_shortcuts_reset_to_plasma_defaults(self):
        plan = installer.build_uninstall_plan(make_installed())
        reset = next(s for s in plan.steps if s.id == "shortcuts")
        # [kwin] entry: the default field becomes the active one again.
        self.assertIn(
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "kwin", "--key", "Window Close",
             "Alt+F4,Alt+F4,Close Window"], reset.commands)
        self.assertIn(BUSCTL + ["kwin", "Window Close", "", "", "1",
                                "150994995"], reset.commands)
        # A cleared Rectangle conflict comes back.
        self.assertIn(BUSCTL + ["kwin", "Switch Window Left", "", "", "1",
                                "419430418"],  # Meta+Alt+Left = 0x19000012
                      reset.commands)
        # [services] entries carry no default; Spectacle's .desktop does.
        self.assertIn(
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "services", "--group", "org.kde.spectacle.desktop",
             "--key", "_launch", "Print\tMeta+Shift+S"], reset.commands)
        self.assertIn(
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "services", "--group", "org.kde.spectacle.desktop",
             "--key", "RecordScreen", "Meta+Alt+R"], reset.commands)
        # The bare-Meta launcher tap comes back: both bindings.
        self.assertIn(BUSCTL + ["plasmashell", "activate application launcher",
                                "", "", "2", "16777250", "150994992"],
                      reset.commands)
        self.assertIn(["kwriteconfig6", "--file", "kwinrc",
                       "--group", "ModifierOnlyShortcuts", "--key", "Meta",
                       "--delete"], reset.commands)
        self.assertEqual(reset.commands[-1],
                         ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"])

    def test_every_installed_binding_is_reset(self):
        plan = installer.build_uninstall_plan(make_installed())
        reset = next(s for s in plan.steps if s.id == "shortcuts")
        written = [c for c in reset.commands if c[:3] == ["kwriteconfig6",
                                                          "--file",
                                                          "kglobalshortcutsrc"]]
        self.assertEqual(len(written), len(installer.KUPERTINO_BINDINGS))
        self.assertEqual(len(written), 20)

    def test_binding_changed_since_install_is_left_alone(self):
        shortcuts = installer.parse_kconfig(REFERENCE_SHORTCUTS)
        shortcuts[(("kwin",), "Window Close")] = "Meta+Q,Alt+F4,Close Window"
        plan = installer.build_uninstall_plan(
            make_installed(kglobalshortcuts=shortcuts))
        reset = next(s for s in plan.steps if s.id == "shortcuts")
        self.assertFalse(any("Window Close" in c for c in reset.commands))

    def test_foreign_keyd_and_konsole_configs_are_left_alone(self):
        plan = installer.build_uninstall_plan(make_installed(
            keyd_config="[ids]\n*\n\n[main]\ncapslock = escape\n",
            konsole_sessionui="<gui name=\"session\"/>\n"))
        ids = [s.id for s in plan.steps]
        self.assertNotIn("keyd-config", ids)
        self.assertNotIn("konsole-copy-paste", ids)

    def test_keyd_removal_stops_keyd_only_without_other_configs(self):
        plan = installer.build_uninstall_plan(make_installed())
        keyd = plan.steps[-1]
        self.assertEqual(keyd.commands[0],
                         ["sudo", "rm", "/etc/keyd/default.conf"])
        self.assertEqual(keyd.commands[1][:2], ["bash", "-c"])
        self.assertIn("then sudo systemctl restart keyd", keyd.commands[1][2])
        self.assertIn("else sudo systemctl disable --now keyd",
                      keyd.commands[1][2])

    def test_snap_removal_disables_then_deletes_script(self):
        plan = installer.build_uninstall_plan(make_installed())
        snap = next(s for s in plan.steps if s.id == "snap")
        self.assertEqual(snap.commands, [
            ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins",
             "--key", "cupertino-snapEnabled", "--delete"],
            ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
            ["rm", "-rf", "/home/u/.local/share/kwin/scripts/cupertino-snap"],
        ])

    def test_packages_and_desktops_are_called_out_as_kept(self):
        plan = installer.build_uninstall_plan(make_installed())
        self.assertTrue(any("keyd" in w and "virtual desktops" in w
                            for w in plan.warnings))


def scripted(answers):
    prompts = []
    feed = iter(answers)

    def ask(prompt):
        prompts.append(prompt)
        return next(feed)

    return ask, prompts


class TestWizard(unittest.TestCase):
    def test_all_yes_selects_every_feature_in_walk_order(self):
        ask, prompts = scripted(["y"] * 9)
        said = []
        selections = installer.run_wizard(installer.FEATURES, ask, said.append)
        self.assertEqual(
            selections,
            ["remap", "textnav", "cmdtab", "cmdq", "screenshots",
             "spaces", "appconv", "rectangle", "theme"],
        )
        self.assertEqual(len(prompts), 9)

    def test_declining_remap_ends_walk_with_nothing_selected(self):
        ask, prompts = scripted(["n"])
        said = []
        selections = installer.run_wizard(installer.FEATURES, ask, said.append)
        self.assertEqual(selections, [])
        self.assertEqual(len(prompts), 1)
        self.assertTrue(any("foundation" in s.lower() for s in said))

    def test_garbage_answer_reprompts_same_feature(self):
        ask, prompts = scripted(["maybe", "y"] + ["n"] * 8)
        selections = installer.run_wizard(
            installer.FEATURES, ask, lambda s: None
        )
        self.assertEqual(selections, ["remap"])
        self.assertEqual(len(prompts), 10)


class TestAuthorizePlan(unittest.TestCase):
    def test_every_step_prompted_and_declined_steps_dropped(self):
        plan = installer.Plan(steps=[
            installer.Step(id="s0", description="install package keyd"),
            installer.Step(id="s1", description="write keyd config"),
            installer.Step(id="s2", description="bind cmd-q"),
        ])
        ask, prompts = scripted(["y", "n", "y"])
        approved = installer.authorize_plan(plan, ask, lambda s: None)
        self.assertEqual([s.id for s in approved], ["s0", "s2"])
        self.assertEqual(len(prompts), 3)
        self.assertIn("write keyd config", prompts[1])


class TestExecute(unittest.TestCase):
    def test_runs_steps_in_order_file_writes_before_commands(self):
        steps = [
            installer.Step(id="a", description="", file_path="/f",
                           file_content="X", commands=[["c1"], ["c2"]]),
            installer.Step(id="b", description="", commands=[["c3"]]),
        ]
        calls, writes = [], []

        def run(argv):
            calls.append(argv)
            return 0

        result = installer.execute(
            steps, run, lambda p, c: writes.append((p, c)), lambda s: None
        )
        self.assertEqual(result.completed, ["a", "b"])
        self.assertIsNone(result.failed)
        self.assertEqual(writes, [("/f", "X")])
        self.assertEqual(calls, [["c1"], ["c2"], ["c3"]])

    def test_failure_aborts_remaining_commands_and_steps(self):
        # If `keyd check` fails, the sudo cp and every later step must not run.
        steps = [
            installer.Step(id="keyd-config", description="",
                           commands=[["keyd", "check", "/s"],
                                     ["sudo", "cp", "/s", "/etc/keyd/x"]]),
            installer.Step(id="cmdq", description="", commands=[["c3"]]),
        ]
        calls = []

        def run(argv):
            calls.append(argv)
            return 1 if argv[0] == "keyd" else 0

        result = installer.execute(steps, run, lambda p, c: None, lambda s: None)
        self.assertEqual(result.failed, "keyd-config")
        self.assertEqual(result.completed, [])
        self.assertEqual(calls, [["keyd", "check", "/s"]])


if __name__ == "__main__":
    unittest.main()
