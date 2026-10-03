import json
import importlib.util
import os
import pathlib
import py_compile
import subprocess
import tempfile
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

    def test_kwin_fallback_does_not_hide_from_unfiltered_windows(self):
        module_path = ROOT / "portable" / "mochi_companion.py"
        spec = importlib.util.spec_from_file_location("mochi_companion_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        fake = subprocess.CompletedProcess([], 0, stdout="11\n12\n", stderr="")
        with mock.patch.object(module.subprocess, "run", return_value=fake):
            self.assertFalse(module.windows_kwin())

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
