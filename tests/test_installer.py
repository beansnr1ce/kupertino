"""Tests for the kupertino interactive installer.

Seams under test (agreed 2026-08-20):
  S1 render_keyd_config(selections)   - pure: assembles /etc/keyd/default.conf
  S2 build_plan(selections, system)   - pure: selections -> ordered install steps
  S3 run_wizard(...)                  - interactive walk, scripted IO
  S4 authorize_plan(...)              - per-step authorization, scripted IO
  S5 execute(...)                     - runs a plan through injected runners

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
        # Values verified live on the reference machine (docs/cupertino-layer.md):
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
        self.assertEqual([s.id for s in plan.steps], ["pkg:keyd", "keyd-config"])

        pkg = plan.steps[0]
        self.assertEqual(
            pkg.commands, [["sudo", "pacman", "-S", "--needed", "keyd"]]
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
            [s.id for s in plan.steps], ["keyd-config", "cmdq", "screenshots"]
        )

        # Entries below are transcribed from the reference machine's working
        # kglobalshortcutsrc ([kwin] entries are active,default,description).
        cmdq = plan.steps[1]
        self.assertEqual(cmdq.commands, [
            ["kwriteconfig6", "--file", "kglobalshortcutsrc",
             "--group", "kwin", "--key", "Window Close",
             "Ctrl+Q\tAlt+F4,Alt+F4,Close Window"],
            BUSCTL + ["kwin", "Window Close", "", "", "2",
                      "67108945", "150994995"],
        ])

        shots = plan.steps[2]
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

    def test_missing_spectacle_on_apt_gets_install_step(self):
        system = make_system(package_manager="apt", installed_packages={"keyd"})
        plan = installer.build_plan(["remap", "screenshots"], system)
        self.assertEqual(plan.steps[0].id, "pkg:spectacle")
        self.assertEqual(
            plan.steps[0].commands, [["sudo", "apt", "install", "spectacle"]]
        )

    def test_unknown_package_manager_warns_instead_of_crashing(self):
        system = make_system(package_manager=None)
        plan = installer.build_plan(["remap"], system)
        self.assertEqual([s.id for s in plan.steps], ["keyd-config"])
        self.assertTrue(any("keyd" in w for w in plan.warnings))

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


def scripted(answers):
    prompts = []
    feed = iter(answers)

    def ask(prompt):
        prompts.append(prompt)
        return next(feed)

    return ask, prompts


class TestWizard(unittest.TestCase):
    def test_all_yes_selects_every_feature_in_walk_order(self):
        ask, prompts = scripted(["y"] * 8)
        said = []
        selections = installer.run_wizard(installer.FEATURES, ask, said.append)
        self.assertEqual(
            selections,
            ["remap", "textnav", "cmdtab", "cmdq", "screenshots",
             "spaces", "appconv", "rectangle"],
        )
        self.assertEqual(len(prompts), 8)

    def test_declining_remap_ends_walk_with_nothing_selected(self):
        ask, prompts = scripted(["n"])
        said = []
        selections = installer.run_wizard(installer.FEATURES, ask, said.append)
        self.assertEqual(selections, [])
        self.assertEqual(len(prompts), 1)
        self.assertTrue(any("foundation" in s.lower() for s in said))

    def test_garbage_answer_reprompts_same_feature(self):
        ask, prompts = scripted(["maybe", "y"] + ["n"] * 7)
        selections = installer.run_wizard(
            installer.FEATURES, ask, lambda s: None
        )
        self.assertEqual(selections, ["remap"])
        self.assertEqual(len(prompts), 9)


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
