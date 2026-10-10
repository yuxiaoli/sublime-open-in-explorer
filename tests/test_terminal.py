"""Terminal dispatch tests; subprocesses are mocked and no terminal is opened."""

import json
import ntpath
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

from test_reveal import FakeSheet, FakeWindow, PROJECT_ROOT, load_plugin


class TerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin, cls.sublime = load_plugin()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="terminal-plugin-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        directory = self.root / "中文 ; $file_path & [x] 'quoted'"
        directory.mkdir()
        self.clicked_file = directory / "inactive ${file}.txt"
        self.clicked_file.write_text("saved content", encoding="utf-8")
        active_file = self.root / "active.txt"
        active_file.write_text("active file", encoding="utf-8")
        self.window = FakeWindow()
        self.window.groups = [
            [FakeSheet(str(active_file), self.window)],
            [FakeSheet(str(active_file), self.window, image=True),
             FakeSheet(str(self.clicked_file), self.window, dirty=True)],
        ]
        self.messages = []
        self.sublime.status_message = self.messages.append
        self.command = self.plugin.OpenInTerminalCommand(self.window)
        self.popen = mock.Mock()
        patcher = mock.patch.object(self.plugin.subprocess, "Popen", self.popen)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Tests run on any OS; never consult the machine's installed terminals.
        patcher = mock.patch.object(self.plugin.shutil, "which", return_value=None)
        self.which = patcher.start()
        self.addCleanup(patcher.stop)

    def available(self, *names):
        self.which.side_effect = lambda name: "/terminals/" + name if name in names else None

    def test_menu_passes_clicked_tab_coordinates(self):
        menu = json.loads((PROJECT_ROOT / "RevealInDefaultExplorer" /
                           "Tab Context.sublime-menu").read_text(encoding="utf-8"))
        entries = [entry for entry in menu if entry.get("command") == "open_in_terminal"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["caption"], "Open in Terminal")
        self.assertEqual(entries[0]["args"], {"group": -1, "index": -1})

    def test_inactive_dirty_tab_in_another_group_opens_its_directory(self):
        self.available("gnome-terminal")
        before = self.clicked_file.read_bytes()
        self.assertTrue(self.command.is_enabled(group=1, index=1))
        self.command.run(group=1, index=1)
        directory = str(self.clicked_file.parent)
        self.popen.assert_called_once_with(
            ["/terminals/gnome-terminal", "--working-directory", directory],
            cwd=directory, shell=False,
        )
        self.assertEqual(self.clicked_file.read_bytes(), before)
        self.assertEqual(self.window.commands, [])
        self.assertEqual(self.messages, [])

    def test_image_tab_opens_its_directory(self):
        self.available("xterm")
        self.assertTrue(self.command.is_enabled(group=1, index=0))
        self.command.run(group=1, index=0)
        self.popen.assert_called_once_with(["/terminals/xterm"], cwd=str(self.root), shell=False)

    def test_invalid_coordinates_do_not_launch_or_fall_back(self):
        for group, index in ((-1, -1), (0, -1), (-1, 0), (20, 0), (1, 20),
                             (True, 0), (1, False), ("1", 0), (None, 0)):
            with self.subTest(group=group, index=index):
                self.assertFalse(self.command.is_enabled(group, index))
                self.command.run(group, index)
        self.popen.assert_not_called()
        self.which.assert_not_called()
        self.assertEqual(self.window.commands, [])

    def test_unsaved_missing_relative_and_directory_paths_do_not_launch(self):
        for path in (None, "", "relative.txt", str(self.root),
                     str(self.root / "missing.txt"), "invalid\x00path"):
            with self.subTest(path=path):
                self.window.groups[1][1].path = path
                self.assertFalse(self.command.is_enabled(1, 1))
                self.command.run(1, 1)
        self.popen.assert_not_called()
        self.which.assert_not_called()

    def test_disappearing_file_is_rechecked(self):
        self.assertTrue(self.command.is_enabled(1, 1))
        self.clicked_file.unlink()
        self.command.run(1, 1)
        self.popen.assert_not_called()
        self.assertIn("missing or inaccessible", self.messages[-1])

    def test_windows_terminal_uses_literal_cwd_without_path_arguments(self):
        self.available("wt.exe", "pwsh.exe")
        with mock.patch.object(self.sublime, "platform", return_value="windows"):
            self.command.run(1, 1)
        self.popen.assert_called_once_with(
            ["/terminals/wt.exe", "-w", "new", "-d", "."],
            cwd=str(self.clicked_file.parent), shell=False,
        )

    def test_windows_drive_root_and_unc_directory_are_preserved(self):
        self.available("wt.exe")
        paths = (r"C:\file.txt", r"C:\中文 ; $folder & [x]\file.txt",
                 r"\\server\share name\$folder;\file.txt")
        for path in paths:
            with self.subTest(path=path):
                self.popen.reset_mock()
                self.window.groups[1][1].path = path
                with mock.patch.object(self.sublime, "platform", return_value="windows"), \
                        mock.patch.object(self.plugin, "os", types.SimpleNamespace(path=ntpath)), \
                        mock.patch.object(ntpath, "isfile", return_value=True):
                    self.command.run(1, 1)
                self.popen.assert_called_once_with(
                    ["/terminals/wt.exe", "-w", "new", "-d", "."],
                    cwd=ntpath.dirname(path), shell=False,
                )

    def test_windows_powershell_fallback_opens_a_new_console(self):
        for name in ("pwsh.exe", "powershell.exe"):
            with self.subTest(name=name):
                self.popen.reset_mock()
                self.available(name)
                with mock.patch.object(self.sublime, "platform", return_value="windows"), \
                        mock.patch.object(self.plugin.subprocess, "CREATE_NEW_CONSOLE", 0x10, create=True):
                    self.command.run(1, 1)
                self.popen.assert_called_once_with(
                    ["/terminals/" + name, "-NoExit"],
                    cwd=str(self.clicked_file.parent), shell=False, creationflags=0x10,
                )

    def test_broken_windows_terminal_alias_falls_back_to_powershell(self):
        self.available("wt.exe", "powershell.exe")
        self.popen.side_effect = [FileNotFoundError("broken alias"), mock.Mock()]
        with mock.patch.object(self.sublime, "platform", return_value="windows"), \
                mock.patch.object(self.plugin.subprocess, "CREATE_NEW_CONSOLE", 0x10, create=True):
            self.command.run(1, 1)
        self.assertEqual(self.popen.call_count, 2)
        self.assertEqual(self.popen.call_args.args[0], ["/terminals/powershell.exe", "-NoExit"])
        self.assertEqual(self.messages, [])

    def test_macos_passes_directory_as_one_argument_to_terminal(self):
        with mock.patch.object(self.sublime, "platform", return_value="osx"):
            self.command.run(1, 1)
        directory = str(self.clicked_file.parent)
        self.popen.assert_called_once_with(
            ["/usr/bin/open", "-a", "Terminal", directory], cwd=directory, shell=False,
        )

    def test_linux_terminal_fallbacks_receive_literal_directory(self):
        directory = str(self.clicked_file.parent)
        for name, args in (("gnome-terminal", ["--working-directory", directory]),
                           ("konsole", ["--workdir", directory]),
                           ("xfce4-terminal", ["--working-directory", directory]),
                           ("xterm", [])):
            with self.subTest(name=name):
                self.popen.reset_mock()
                self.available(name)
                self.command.run(1, 1)
                self.popen.assert_called_once_with(
                    ["/terminals/" + name] + args, cwd=directory, shell=False,
                )

    def test_missing_terminal_reports_a_useful_error(self):
        for platform in ("windows", "linux", "unknown"):
            with self.subTest(platform=platform):
                self.messages.clear()
                with mock.patch.object(self.sublime, "platform", return_value=platform):
                    self.command.run(1, 1)
                self.popen.assert_not_called()
                self.assertIn("Open in Terminal: could not start a terminal:", self.messages[-1])

    def test_launch_failure_reports_status_without_claiming_success(self):
        self.available("gnome-terminal")
        self.popen.side_effect = PermissionError("launch denied")
        self.command.run(1, 1)
        self.assertIn("launch denied", self.messages[-1])
        self.assertEqual(len(self.messages), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
