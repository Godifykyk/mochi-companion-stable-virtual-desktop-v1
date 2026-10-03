import json
import importlib.util
import os
import pathlib
import py_compile
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


class StableReleaseTests(unittest.TestCase):
    def test_shared_catalog_is_complete_and_fixed_palette(self):
        catalog = json.loads((ROOT / "shared" / "anime_modes.json").read_text())
        self.assertGreaterEqual(len(catalog["modes"]), 120)
        self.assertTrue({frame[2] for frame in catalog["frames"].values()} <= {"#FFFFFF", "#53C7FF"})

    def test_portable_core_compiles_and_has_supported_backends(self):
        app = ROOT / "portable" / "mochi_companion.py"
        py_compile.compile(str(app), doraise=True)
        source = app.read_text()
        self.assertIn("/usr/share/mochi-companion/shared", source)
        for backend in ("hyprland", "niri", "sway", "x11", "kwin"):
            self.assertIn(f'def windows_{backend}', source)
        self.assertIn("GtkLayerShell", source)
        self.assertIn("--smoke-test", source)
        self.assertIn('gi.require_version("Gdk", "3.0")', source)
        self.assertIn("width * 0.32", source)
        self.assertIn("width * 0.68", source)

    def test_catalog_lookup_has_no_working_directory_override(self):
        source = (ROOT / "portable" / "mochi_companion.py").read_text()
        self.assertNotIn('pathlib.Path(os.environ.get("MOCHI_DATA_DIR", ""))', source)

    def test_nix_wrapper_sets_catalog_directory(self):
        expression = (ROOT / "packages" / "nix" / "default.nix").read_text()
        self.assertIn("--set MOCHI_DATA_DIR", expression)

    def test_distribution_packages_install_desktop_entry(self):
        desktop_name = "io.github.mochi.Companion.desktop"
        self.assertIn(desktop_name, (ROOT / "packages" / "arch" / "PKGBUILD").read_text())
        self.assertIn(desktop_name, (ROOT / "packages" / "fedora" / "mochi-companion.spec").read_text())
        self.assertIn(desktop_name, (ROOT / "packages" / "nix" / "default.nix").read_text())
        install_rules = ROOT / "packages" / "debian" / "rules"
        self.assertTrue(install_rules.is_file())
        self.assertIn(desktop_name, install_rules.read_text())

    def test_kwin_fallback_does_not_hide_from_unfiltered_windows(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        fake = subprocess.CompletedProcess([], 0, stdout="11\n12\n", stderr="")
        with mock.patch.object(module.subprocess, "run", return_value=fake):
            self.assertFalse(module.windows_kwin())

    def test_kde_x11_uses_workspace_aware_x11_backend(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_kde_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        env = {"XDG_CURRENT_DESKTOP": "KDE", "XDG_SESSION_DESKTOP": "KDE", "XDG_SESSION_TYPE": "x11"}
        with mock.patch.dict(module.os.environ, env, clear=True):
            self.assertIs(module.select_window_backend(), module.windows_x11)

    def test_sway_counts_untitled_application_windows(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_sway_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        workspaces = [{"name": "1", "focused": True}]
        tree = {
            "type": "root",
            "nodes": [{"type": "workspace", "name": "1", "nodes": [{"type": "con", "name": None, "app_id": "foot", "nodes": [], "floating_nodes": []}], "floating_nodes": []}],
            "floating_nodes": [],
        }
        with mock.patch.object(module, "command_json", side_effect=[workspaces, tree]):
            self.assertTrue(module.windows_sway())

    def test_wayland_self_window_is_excluded_and_layer_shell_is_checked(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_self_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        hypr_workspace = {"id": 1}
        hypr_clients = [{"workspace": {"id": 1}, "class": "io.github.mochi.Companion", "title": "Mochi Companion"}]
        with mock.patch.object(module, "command_json", side_effect=[hypr_workspace, hypr_clients]):
            self.assertFalse(module.windows_hyprland())
        source = module_path.read_text()
        self.assertIn("GLib.set_prgname(APP_ID)", source)
        self.assertIn("GtkLayerShell.is_supported()", source)

    def test_niri_uses_focused_workspace_on_multi_monitor_setups(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_niri_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        workspaces = [
            {"id": 1, "is_active": True, "is_focused": True},
            {"id": 2, "is_active": True, "is_focused": False},
        ]
        windows = [{"workspace_id": 2, "app_id": "firefox"}]
        with mock.patch.object(module, "command_json", side_effect=[workspaces, windows]):
            self.assertFalse(module.windows_niri())

    def test_x11_smart_hide_checks_only_active_workspace(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_x11_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        responses = {
            ("wmctrl", "-d"): subprocess.CompletedProcess([], 0, stdout="0  * DG: 1920x1080  VP: 0,0  WA: 0,0 1920x1040  one\n1  - DG: 1920x1080  VP: N/A  WA: 0,0 1920x1040  two\n", stderr=""),
            ("wmctrl", "-l"): subprocess.CompletedProcess([], 0, stdout="0x01  1 host Other workspace\n", stderr=""),
        }
        with mock.patch.object(module.subprocess, "run", side_effect=lambda command, **_kwargs: responses[tuple(command)]):
            self.assertFalse(module.windows_x11())

    def test_x11_smart_hide_rejects_failed_wmctrl_output(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_x11_failure_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        failed = subprocess.CompletedProcess([], 1, stdout="diagnostic text\n", stderr="failure")
        with mock.patch.object(module.subprocess, "run", return_value=failed):
            self.assertFalse(module.windows_x11())

    def test_smart_hide_unmaps_window_instead_of_using_invisible_surface(self):
        source = (ROOT / "portable" / "mochi_companion.py").read_text()
        smart_hide = source.split("def smart_hide(self)", 1)[1].split("def on_click", 1)[0]
        self.assertIn("self.hide()", smart_hide)
        self.assertIn("self.show_all()", smart_hide)
        self.assertNotIn("set_opacity", smart_hide)

    def test_window_probe_never_blocks_the_ui_caller(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_probe_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def slow_backend():
            time.sleep(0.2)
            return True

        probe = module.WindowOccupancyProbe(slow_backend)
        started = time.monotonic()
        self.assertFalse(probe.refresh())
        self.assertLess(time.monotonic() - started, 0.05)
        time.sleep(0.25)
        self.assertTrue(probe.refresh())

    def test_animation_keeps_first_frame_for_first_tick(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_frame_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        index, drawn = module.advance_frame(["first", "second"], 0, False)
        self.assertEqual(index, 0)
        self.assertTrue(drawn)
        index, drawn = module.advance_frame(["first", "second"], index, drawn)
        self.assertEqual(index, 1)

    def test_invalid_adapter_leaves_no_partial_install(self):
        with tempfile.TemporaryDirectory() as home:
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "invalid"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((pathlib.Path(home) / "data" / "mochi-companion").exists())

    def test_gnome_reinstall_does_not_nest_adapter_directory(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            helper = fake_bin / "gnome-extensions"
            helper.write_text("#!/bin/sh\nexit 0\n")
            helper.chmod(0o755)
            shell = fake_bin / "gnome-shell"
            shell.write_text("#!/bin/sh\necho 'GNOME Shell 49.1'\n")
            shell.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            command = [str(ROOT / "install.sh"), "--adapter", "gnome"]
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            extension = home_path / "data" / "gnome-shell" / "extensions" / "mochi-companion@local.github.io"
            self.assertTrue((extension / "extension.js").is_file())
            self.assertFalse((extension / "gnome-shell-45-plus").exists())

    def test_uninstall_removes_only_recorded_adapter(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            self.assertEqual(subprocess.run([str(ROOT / "install.sh"), "--adapter", "portable"], env=env).returncode, 0)
            unrelated = home_path / "data" / "gnome-shell" / "extensions" / "mochi-companion@local.github.io"
            unrelated.mkdir(parents=True)
            marker = unrelated / "unrelated"
            marker.write_text("keep")
            self.assertEqual(subprocess.run([str(ROOT / "uninstall.sh")], env=env).returncode, 0)
            self.assertTrue(marker.is_file())

    def test_portable_install_refuses_to_overwrite_unowned_autostart(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            autostart = home_path / "config" / "autostart" / "mochi-companion.desktop"
            autostart.parent.mkdir(parents=True)
            autostart.write_text("[Desktop Entry]\nName=Unrelated\n")
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "portable"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(autostart.read_text(), "[Desktop Entry]\nName=Unrelated\n")

    def test_no_autostart_removes_previous_owned_entry(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            command = [str(ROOT / "install.sh"), "--adapter", "portable"]
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            autostart = home_path / "config" / "autostart" / "mochi-companion.desktop"
            self.assertTrue(autostart.is_file())
            self.assertEqual(subprocess.run(command + ["--no-autostart"], env=env).returncode, 0)
            self.assertFalse(autostart.exists())

    def test_failed_noctalia_enable_rolls_back_registered_source(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins enable'*) exit 7 ;;\n"
                "  *'plugins source remove'*) touch \"$HOME/source-removed\"; exit 0 ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "noctalia"], env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((home_path / "source-removed").is_file())
            self.assertFalse((home_path / "data" / "mochi-companion" / "install-state").exists())

    def test_native_uninstall_failure_retains_state_for_retry(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            dest = home_path / "data" / "mochi-companion"
            dest.mkdir(parents=True)
            (dest / "install-state").write_text("noctalia\n")
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text("#!/bin/sh\nexit 9\n")
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "uninstall.sh")], env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((dest / "install-state").is_file())

    def test_reinstall_removes_obsolete_payload_files(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            command = [str(ROOT / "install.sh"), "--adapter", "portable"]
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            obsolete = home_path / "data" / "mochi-companion" / "shared" / "obsolete.file"
            obsolete.write_text("old")
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            self.assertFalse(obsolete.exists())

    def test_kde_reinstall_uses_upgrade_operation(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            tool = fake_bin / "kpackagetool6"
            tool.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$HOME/kpackage.log\"\n")
            tool.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            command = [str(ROOT / "install.sh"), "--adapter", "kde"]
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            log = (home_path / "kpackage.log").read_text()
            self.assertIn("--install", log)
            self.assertIn("--upgrade", log)

    def test_auto_rejects_unsupported_gnome_shell_version(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            for name, body in {
                "gnome-extensions": "#!/bin/sh\nexit 0\n",
                "gnome-shell": "#!/bin/sh\necho 'GNOME Shell 44.9'\n",
            }.items():
                helper = fake_bin / name
                helper.write_text(body)
                helper.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_CURRENT_DESKTOP": "GNOME",
                "XDG_SESSION_DESKTOP": "GNOME",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "auto"], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Installed adapter: portable", result.stdout)

    def test_native_adapter_manifests(self):
        kde = json.loads((ROOT / "adapters" / "kde-plasma-6" / "package" / "metadata.json").read_text())
        self.assertEqual(kde["KPackageStructure"], "Plasma/Applet")
        self.assertEqual(kde["X-Plasma-API-Minimum-Version"], "6.0")
        gnome = json.loads((ROOT / "adapters" / "gnome-shell-45-plus" / "metadata.json").read_text())
        self.assertIn("45", gnome["shell-version"])
        self.assertTrue((ROOT / "adapters" / "noctalia" / "mochi-eyes" / "plugin.toml").is_file())

    def test_kde_preserves_standard_right_click_context_menu(self):
        qml = (ROOT / "adapters" / "kde-plasma-6" / "package" / "contents" / "ui" / "main.qml").read_text()
        self.assertNotIn("acceptedButtons: Qt.AllButtons", qml)
        self.assertIn("acceptedButtons: Qt.LeftButton | Qt.MiddleButton", qml)

    def test_native_adapter_catalogs_have_no_dangling_assets(self):
        catalogs = [
            ROOT / "adapters" / "kde-plasma-6" / "package" / "contents" / "data" / "anime_modes.json",
            ROOT / "adapters" / "gnome-shell-45-plus" / "anime_modes.json",
        ]
        for path in catalogs:
            catalog = json.loads(path.read_text())
            for mode in catalog["modes"]:
                self.assertNotIn("gif", mode, f"{path}: {mode['id']}")
                self.assertNotIn("animation_frames", mode, f"{path}: {mode['id']}")

    def test_noctalia_activity_callback_cannot_override_newer_interaction(self):
        source = (ROOT / "adapters" / "noctalia" / "mochi-eyes" / "mochi.luau").read_text()
        self.assertIn("local stateGeneration = 0", source)
        self.assertIn("if generation ~= stateGeneration then return end", source)
        self.assertIn("currentMode == nil and temporaryTicks == 0 and not pointerInside", source)

    def test_install_refuses_symlinked_destination(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            shared = home_path / "shared-data"
            shared.mkdir()
            marker = shared / "important.txt"
            marker.write_text("keep")
            data = home_path / "data"
            data.mkdir()
            (data / "mochi-companion").symlink_to(shared, target_is_directory=True)
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": str(data), "XDG_CONFIG_HOME": f"{home}/config"}
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "portable"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), "keep")

    def test_portable_install_refuses_to_replace_unowned_launcher_symlink(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            bin_dir = home_path / ".local" / "bin"
            bin_dir.mkdir(parents=True)
            unrelated = home_path / "unrelated-program"
            unrelated.write_text("keep")
            launcher = bin_dir / "mochi-companion"
            launcher.symlink_to(unrelated)
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "portable"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(launcher.resolve(), unrelated)
            self.assertEqual(unrelated.read_text(), "keep")

    def test_noctalia_install_verifies_asynchronous_enablement(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins source remove'*) touch \"$HOME/source-removed\"; exit 0 ;;\n"
                "  *'plugins list'*) echo 'kanha/mochi-eyes [mochi-stable] 1.0.0 disabled'; exit 0 ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
                "MOCHI_NOCTALIA_VERIFY_ATTEMPTS": "2",
                "MOCHI_NOCTALIA_VERIFY_DELAY": "0",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "noctalia"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((home_path / "source-removed").is_file())
            self.assertFalse((home_path / "data" / "mochi-companion").exists())

    def test_noctalia_enable_verification_does_not_cross_plugin_lines(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins source remove'*) exit 0 ;;\n"
                "  *'plugins list'*) printf '%s\\n' 'kanha/mochi-eyes [mochi-stable] 1.0.0 disabled' 'other/plugin [community] 1.0.0 enabled'; exit 0 ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
                "MOCHI_NOCTALIA_VERIFY_ATTEMPTS": "1",
                "MOCHI_NOCTALIA_VERIFY_DELAY": "0",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "noctalia"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((home_path / "data" / "mochi-companion").exists())

    def test_failed_noctalia_reinstall_restores_payload_before_source_refresh(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            dest = home_path / "data" / "mochi-companion"
            (dest / "adapters" / "noctalia").mkdir(parents=True)
            (dest / "adapters" / "noctalia" / "old-marker").write_text("old")
            (dest / "install-state").write_text("noctalia\n")
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins update'*) if [ -f \"$XDG_DATA_HOME/mochi-companion/adapters/noctalia/old-marker\" ]; then echo old >> \"$HOME/update.log\"; else echo new >> \"$HOME/update.log\"; fi; exit 0 ;;\n"
                "  *'plugins list'*) echo 'kanha/mochi-eyes [mochi-stable] 1.0.0 disabled'; exit 0 ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
                "MOCHI_NOCTALIA_VERIFY_ATTEMPTS": "1",
                "MOCHI_NOCTALIA_VERIFY_DELAY": "0",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "noctalia"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((home_path / "update.log").read_text().splitlines(), ["new", "old"])
            self.assertTrue((dest / "adapters" / "noctalia" / "old-marker").is_file())

    def test_failed_external_rollback_retains_payload_and_state_for_retry(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins enable'*) exit 7 ;;\n"
                "  *'plugins source remove'*) exit 9 ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "noctalia"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            state = home_path / "data" / "mochi-companion" / "install-state"
            self.assertEqual(state.read_text(), "noctalia\n")
            self.assertIn("Rollback incomplete", result.stderr)

    def test_failed_noctalia_update_refreshes_restored_payload(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            dest = home_path / "data" / "mochi-companion"
            (dest / "adapters" / "noctalia").mkdir(parents=True)
            (dest / "adapters" / "noctalia" / "old-marker").write_text("old")
            (dest / "install-state").write_text("noctalia\n")
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins update'*) if [ -f \"$XDG_DATA_HOME/mochi-companion/adapters/noctalia/old-marker\" ]; then echo old >> \"$HOME/update.log\"; exit 0; else echo new >> \"$HOME/update.log\"; exit 7; fi ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "noctalia"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((home_path / "update.log").read_text().splitlines(), ["new", "old"])
            self.assertTrue((dest / "adapters" / "noctalia" / "old-marker").is_file())

    def test_failed_payload_removal_retains_state_for_cleanup_retry(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "fake-bin"
            fake_bin.mkdir()
            ln = fake_bin / "ln"
            ln.write_text(
                "#!/bin/sh\n"
                "/usr/bin/ln \"$@\" || exit $?\n"
                "/usr/bin/chmod 500 \"$XDG_DATA_HOME/mochi-companion\"\n"
            )
            ln.chmod(0o755)
            rm = fake_bin / "rm"
            rm.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in *\"$XDG_DATA_HOME/mochi-companion\"*) exit 9 ;; *) exec /usr/bin/rm \"$@\" ;; esac\n"
            )
            rm.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "portable"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            state = home_path / "data" / "mochi-companion" / "install-state"
            self.assertEqual(state.read_text(), "portable\n")
            self.assertIn("Rollback incomplete", result.stderr)

    def test_kde_uninstall_is_idempotent_when_package_is_already_absent(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            dest = home_path / "data" / "mochi-companion"
            dest.mkdir(parents=True)
            (dest / "install-state").write_text("kde\n")
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            tool = fake_bin / "kpackagetool6"
            tool.write_text("#!/bin/sh\ncase \"$*\" in *--list*) exit 0 ;; *) exit 9 ;; esac\n")
            tool.chmod(0o755)
            env = os.environ | {"HOME": home, "PATH": f"{fake_bin}:/usr/bin:/bin", "XDG_DATA_HOME": f"{home}/data"}
            result = subprocess.run([str(ROOT / "uninstall.sh")], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(dest.exists())

    def test_late_portable_failure_rolls_back_launcher_and_autostart(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            fake_bin = home_path / "fake-bin"
            fake_bin.mkdir()
            ln = fake_bin / "ln"
            ln.write_text(
                "#!/bin/sh\n"
                "/usr/bin/ln \"$@\" || exit $?\n"
                "/usr/bin/chmod 500 \"$XDG_DATA_HOME/mochi-companion\"\n"
            )
            ln.chmod(0o755)
            env = os.environ | {
                "HOME": home,
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
                "XDG_DATA_HOME": f"{home}/data",
                "XDG_CONFIG_HOME": f"{home}/config",
            }
            result = subprocess.run([str(ROOT / "install.sh"), "--adapter", "portable"], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((home_path / ".local" / "bin" / "mochi-companion").exists())
            self.assertFalse((home_path / "config" / "autostart" / "mochi-companion.desktop").exists())
            self.assertFalse((home_path / "data" / "mochi-companion").exists())

    def test_failed_reinstall_payload_copy_restores_previous_install(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            env = os.environ | {"HOME": home, "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            command = [str(ROOT / "install.sh"), "--adapter", "portable"]
            self.assertEqual(subprocess.run(command, env=env).returncode, 0)
            dest = home_path / "data" / "mochi-companion"
            marker = dest / "shared" / "previous-install.txt"
            marker.write_text("keep")
            fake_bin = home_path / "bin"
            fake_bin.mkdir(exist_ok=True)
            cp = fake_bin / "cp"
            cp.write_text("#!/bin/sh\nexit 7\n")
            cp.chmod(0o755)
            failed_env = env | {"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}
            result = subprocess.run(command, env=failed_env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), "keep")
            self.assertEqual((dest / "install-state").read_text(), "portable\n")

    def test_native_uninstall_retains_state_when_required_tool_is_unavailable(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            dest = home_path / "data" / "mochi-companion"
            dest.mkdir(parents=True)
            (dest / "install-state").write_text("noctalia\n")
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            (fake_bin / "bash").symlink_to("/usr/bin/bash")
            env = {"HOME": home, "PATH": str(fake_bin), "XDG_DATA_HOME": f"{home}/data", "XDG_CONFIG_HOME": f"{home}/config"}
            result = subprocess.run([str(ROOT / "uninstall.sh")], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((dest / "install-state").is_file())

    def test_noctalia_uninstall_is_idempotent_when_plugin_and_source_are_already_absent(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            dest = home_path / "data" / "mochi-companion"
            dest.mkdir(parents=True)
            (dest / "install-state").write_text("noctalia\n")
            fake_bin = home_path / "bin"
            fake_bin.mkdir()
            noctalia = fake_bin / "noctalia"
            noctalia.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *'plugins list'*) exit 0 ;;\n"
                "  *'plugins source list'*) exit 0 ;;\n"
                "  *) exit 9 ;;\n"
                "esac\n"
            )
            noctalia.chmod(0o755)
            env = os.environ | {"HOME": home, "PATH": f"{fake_bin}:/usr/bin:/bin", "XDG_DATA_HOME": f"{home}/data"}
            result = subprocess.run([str(ROOT / "uninstall.sh")], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(dest.exists())

    def test_noctalia_manifest_uses_current_stable_api_without_unreleased_tooltips(self):
        plugin = (ROOT / "adapters" / "noctalia" / "mochi-eyes" / "plugin.toml").read_text()
        source = (ROOT / "adapters" / "noctalia" / "mochi-eyes" / "mochi.luau").read_text()
        self.assertIn('plugin_api = 32', plugin)
        self.assertNotIn("tooltip =", source)

    def test_debian_native_package_uses_native_version_and_installs_launcher_name(self):
        changelog = (ROOT / "packages" / "debian" / "changelog").read_text()
        control = (ROOT / "packages" / "debian" / "control").read_text()
        rules = (ROOT / "packages" / "debian" / "rules").read_text()
        self.assertTrue(changelog.startswith("mochi-companion (1.0.0)"))
        self.assertIn("Build-Depends: debhelper-compat (= 13), python3", control)
        self.assertIn("usr/bin/mochi-companion", rules)

    def test_installer_scripts_parse(self):
        for name in ("install.sh", "uninstall.sh", "scripts/detect-environment.sh"):
            result = subprocess.run(["bash", "-n", str(ROOT / name)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_compatibility_matrix_covers_ten_desktops_and_distros(self):
        matrix = (ROOT / "docs" / "COMPATIBILITY.md").read_text()
        desktops = ["Hyprland", "KDE Plasma", "GNOME", "Xfce", "Cinnamon", "MATE", "LXQt", "Budgie", "Sway", "Niri"]
        distros = ["Arch Linux", "Ubuntu", "Debian", "Fedora", "openSUSE", "Linux Mint", "Manjaro", "Pop!_OS", "NixOS", "Void Linux"]
        for name in desktops + distros:
            self.assertIn(name, matrix)

    def test_github_release_files_exist(self):
        for path in ("README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", ".gitignore", "CHANGELOG.md"):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
