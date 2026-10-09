"""Installer tests use isolated temporary profiles, never live Sublime directories."""

import importlib.util
import io
from contextlib import redirect_stdout
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = PROJECT_ROOT / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("installer_under_test", INSTALL_SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sublime install 空间 ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        for relative, name in installer.SOURCE_FILES:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Fixture for " + name + "\n", encoding="utf-8")
        self.data = self.root / "custom data 数据"
        self.data.mkdir()
        self.target = self.data / "Installed Packages"
        self.package = self.target / installer.PACKAGE_NAME

    def snapshot(self):
        return sorted((str(path.relative_to(self.root)),
                       path.read_bytes() if path.is_file() else None)
                      for path in self.root.rglob("*"))

    def write_existing(self, content=b"older package"):
        self.target.mkdir(exist_ok=True)
        self.package.write_bytes(content)

    def test_first_install_in_path_with_spaces_and_unicode(self):
        result = installer.install(self.source, self.target)
        self.assertIn("Installed:", result)
        self.assertIn("Restart Sublime Text", result)
        self.assertEqual(self.package.read_bytes(), installer.build_package(self.source))
        self.assertEqual(list(self.target.iterdir()), [self.package])

    def test_payload_contains_only_allowlisted_files(self):
        for relative in (".env", ".git/config", "tests/test_secret.py", "scripts/extra.py",
                         "RevealInDefaultExplorer/__pycache__/secret.pyc"):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("must never ship", encoding="utf-8")
        payload = installer.build_package(self.source)
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            self.assertIsNone(bundle.testzip())
            self.assertEqual(set(bundle.namelist()),
                             {".python-version", "RevealInDefaultExplorer.py",
                              "Tab Context.sublime-menu", "README.md", "LICENSE"})
            for relative, name in installer.SOURCE_FILES:
                self.assertEqual(bundle.read(name), (self.source / relative).read_bytes())
        self.assertEqual(payload, installer.build_package(self.source))

    def test_payload_matches_existing_builder(self):
        spec = importlib.util.spec_from_file_location("builder_under_test",
                                                    PROJECT_ROOT / "scripts" / "build.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        (self.source / ".gitignore").write_text("fixture\n", encoding="utf-8")
        output = self.root / "dist"
        with mock.patch.object(builder, "ROOT", self.source), \
                mock.patch.object(builder, "DIST", output), redirect_stdout(io.StringIO()):
            builder.main()
        expected = output / "RevealInDefaultExplorer.sublime-package"
        self.assertEqual(installer.build_package(self.source), expected.read_bytes())

    def test_identical_repeat_is_noop_even_with_update(self):
        installer.install(self.source, self.target)
        before = self.snapshot()
        for update in (False, True):
            self.assertIn("Already up to date", installer.install(self.source, self.target,
                                                                 update=update))
            self.assertEqual(self.snapshot(), before)

    def test_different_package_requires_update_without_mutation(self):
        self.write_existing()
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, "--update"):
            installer.install(self.source, self.target)
        self.assertEqual(self.snapshot(), before)

    def test_update_preserves_original_and_prior_backups(self):
        self.write_existing()
        prior = self.target / (installer.PACKAGE_NAME + ".older.bak")
        prior.write_bytes(b"earlier backup")
        result = installer.install(self.source, self.target, update=True)
        backups = [path for path in self.target.glob("*.bak") if path != prior]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"older package")
        self.assertTrue(backups[0].name.endswith(".bak"))
        self.assertIn(str(backups[0]), result)
        self.assertEqual(prior.read_bytes(), b"earlier backup")
        self.assertEqual(self.package.read_bytes(), installer.build_package(self.source))

    def test_dry_run_first_install_creates_nothing(self):
        before = self.snapshot()
        self.assertIn("would install", installer.install(self.source, self.target, dry_run=True))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.target.exists())

    def test_dry_run_update_creates_no_backup_or_changes(self):
        self.write_existing()
        before = self.snapshot()
        result = installer.install(self.source, self.target, dry_run=True, update=True)
        self.assertIn("back up and replace", result)
        self.assertEqual(self.snapshot(), before)

    def test_dry_run_obeys_update_permission(self):
        self.write_existing()
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, "--update"):
            installer.install(self.source, self.target, dry_run=True)
        self.assertEqual(self.snapshot(), before)

    def test_missing_parent_wrong_name_and_file_target_are_rejected(self):
        invalid = [self.root / "missing" / "Installed Packages", self.data / "Packages"]
        self.target.write_text("not a directory", encoding="utf-8")
        invalid.append(self.target)
        before = self.snapshot()
        for target in invalid:
            with self.subTest(target=str(target)), self.assertRaises(installer.InstallError):
                installer.install(self.source, target)
        self.assertEqual(self.snapshot(), before)

    def test_missing_source_has_no_destination_side_effects(self):
        (self.source / "LICENSE").unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, "Required source"):
            installer.install(self.source, self.target)
        self.assertEqual(self.snapshot(), before)

    def test_unrelated_packages_and_user_settings_are_preserved(self):
        self.target.mkdir()
        other = self.target / "AnotherPackage.sublime-package"
        other.write_bytes(b"unrelated")
        settings = self.data / "Packages" / "User" / "Preferences.sublime-settings"
        settings.parent.mkdir(parents=True)
        settings.write_bytes(b'{"color_scheme": "my choice"}\n')
        installer.install(self.source, self.target)
        self.assertEqual(other.read_bytes(), b"unrelated")
        self.assertEqual(settings.read_bytes(), b'{"color_scheme": "my choice"}\n')

    def test_unpacked_duplicate_is_rejected(self):
        duplicate = self.data / "Packages" / "RevealInDefaultExplorer"
        duplicate.mkdir(parents=True)
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, "unpacked plugin"):
            installer.install(self.source, self.target)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_target_and_package_are_rejected(self):
        other = self.root / "other"
        other.mkdir()
        try:
            self.target.symlink_to(other, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable in this test environment")
        with self.assertRaisesRegex(installer.InstallError, "symlink"):
            installer.install(self.source, self.target)
        self.target.unlink()
        self.target.mkdir()
        original = other / "original"
        original.write_bytes(b"do not change")
        self.package.symlink_to(original)
        with self.assertRaisesRegex(installer.InstallError, "unsafe existing package"):
            installer.install(self.source, self.target, update=True)
        self.assertEqual(original.read_bytes(), b"do not change")

    def test_symlink_source_is_rejected(self):
        source = self.source / "LICENSE"
        source.unlink()
        try:
            source.symlink_to(self.source / "README.md")
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable in this test environment")
        with self.assertRaisesRegex(installer.InstallError, "Required source"):
            installer.install(self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_failed_atomic_replace_keeps_old_package_and_cleans_temporary(self):
        self.write_existing()
        with mock.patch.object(installer.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                installer.install(self.source, self.target, update=True)
        self.assertEqual(self.package.read_bytes(), b"older package")
        self.assertEqual(list(self.target.glob("*.tmp")), [])
        self.assertEqual(len(list(self.target.glob("*.bak"))), 1)

    def test_failed_backup_keeps_old_package_and_cleans_new_temporary(self):
        self.write_existing()
        real_write = installer.write_temporary

        def fail_backup(target, payload, suffix):
            if suffix == ".bak":
                raise OSError("backup failed")
            return real_write(target, payload, suffix)

        with mock.patch.object(installer, "write_temporary", side_effect=fail_backup):
            with self.assertRaisesRegex(OSError, "backup failed"):
                installer.install(self.source, self.target, update=True)
        self.assertEqual(self.package.read_bytes(), b"older package")
        self.assertEqual(list(self.target.iterdir()), [self.package])

    def test_failed_file_flush_cleans_partial_file_and_preserves_old_package(self):
        self.write_existing()
        with mock.patch.object(installer.os, "fsync", side_effect=OSError("flush failed")):
            with self.assertRaisesRegex(OSError, "flush failed"):
                installer.install(self.source, self.target, update=True)
        self.assertEqual(self.package.read_bytes(), b"older package")
        self.assertEqual(list(self.target.iterdir()), [self.package])

    def test_change_during_install_is_rejected(self):
        self.write_existing()
        real_write = installer.write_temporary

        def write_then_change(*args):
            temporary = real_write(*args)
            self.package.write_bytes(b"changed concurrently")
            return temporary

        with mock.patch.object(installer, "write_temporary", side_effect=write_then_change):
            with self.assertRaisesRegex(installer.InstallError, "changed during installation"):
                installer.install(self.source, self.target, update=True)
        self.assertEqual(self.package.read_bytes(), b"changed concurrently")
        self.assertEqual(list(self.target.glob("*.tmp")), [])
        self.assertEqual(list(self.target.glob("*.bak")), [])

    def test_package_appearing_at_first_publication_is_preserved(self):
        real_link = installer.os.link

        def publish_competing_package(source, destination):
            Path(destination).write_bytes(b"arrived concurrently")
            return real_link(source, destination)

        with mock.patch.object(installer.os, "link", side_effect=publish_competing_package):
            with self.assertRaisesRegex(installer.InstallError, "appeared during installation"):
                installer.install(self.source, self.target)
        self.assertEqual(self.package.read_bytes(), b"arrived concurrently")
        self.assertEqual(list(self.target.iterdir()), [self.package])

    def test_first_install_fails_safely_when_hard_links_are_unavailable(self):
        with mock.patch.object(installer.os, "link", side_effect=OSError("not supported")):
            with self.assertRaisesRegex(installer.InstallError, "filesystem supporting hard links"):
                installer.install(self.source, self.target)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_change_during_backup_is_preserved_with_original_backup(self):
        self.write_existing()
        real_write = installer.write_temporary

        def backup_then_change(target, payload, suffix):
            path = real_write(target, payload, suffix)
            if suffix == ".bak":
                self.package.write_bytes(b"changed during backup")
            return path

        with mock.patch.object(installer, "write_temporary", side_effect=backup_then_change):
            with self.assertRaisesRegex(installer.InstallError, "changed while backing it up"):
                installer.install(self.source, self.target, update=True)
        self.assertEqual(self.package.read_bytes(), b"changed during backup")
        backups = list(self.target.glob("*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"older package")
        self.assertEqual(list(self.target.glob("*.tmp")), [])

    def test_platform_discovery_paths_use_only_current_defaults(self):
        home = self.root / "home"
        appdata = self.root / "App Data"
        xdg = self.root / "xdg"
        cases = (
            ("win32", {"APPDATA": str(appdata)}, appdata / "Sublime Text"),
            ("darwin", {}, home / "Library" / "Application Support" / "Sublime Text"),
            ("linux", {}, home / ".config" / "sublime-text"),
            ("linux", {"XDG_CONFIG_HOME": str(xdg)}, xdg / "sublime-text"),
        )
        for platform, environ, expected in cases:
            with self.subTest(platform=platform, environ=environ):
                self.assertEqual(installer.default_data_roots(platform, environ, home), [expected])
        self.assertEqual(installer.default_data_roots("win32", {}, home), [])
        for platform, environ in (("win32", {"APPDATA": "relative"}),
                                  ("linux", {"XDG_CONFIG_HOME": "relative"}), ("unknown", {})):
            with self.subTest(platform=platform), self.assertRaises(installer.InstallError):
                installer.default_data_roots(platform, environ, home)

    def test_discovery_requires_one_existing_data_root(self):
        missing = self.root / "missing profile"
        with mock.patch.object(installer, "default_data_roots", return_value=[missing]):
            with self.assertRaisesRegex(installer.InstallError, "No existing"):
                installer.discover_target()
        with mock.patch.object(installer, "default_data_roots", return_value=[self.data]):
            self.assertEqual(installer.discover_target(), self.target)
        another = self.root / "second profile"
        another.mkdir()
        with mock.patch.object(installer, "default_data_roots", return_value=[self.data, another]):
            with self.assertRaisesRegex(installer.InstallError, "Multiple"):
                installer.discover_target()

    def test_cli_dry_run_and_invalid_target_exit_codes(self):
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(INSTALL_SCRIPT), "--target", str(self.target),
                                 "--dry-run"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run:", result.stdout)
        self.assertEqual(self.snapshot(), before)
        result = subprocess.run([sys.executable, str(INSTALL_SCRIPT), "--target",
                                 str(self.root / "missing" / "Installed Packages")],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("parent data directory must already exist", result.stderr)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
