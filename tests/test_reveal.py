"""Unit tests with minimal Sublime stubs; these are not editor or Explorer QA."""

import importlib.util
import json
import ntpath
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_FILE = PROJECT_ROOT / "RevealInDefaultExplorer" / "RevealInDefaultExplorer.py"


def decode_literal_argument(value):
    """Decode the assumed snippet literal subset, without calling plugin code.

    This unit-only check is not a replacement for sublime.expand_variables()
    or a real editor test. A literal argument must escape every dollar sign
    and backslash, preventing it from introducing a snippet variable.
    """
    output = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "$":
            raise AssertionError("Unescaped dollar sign in open_dir argument")
        if char == "\\":
            if index + 1 >= len(value) or value[index + 1] not in ("\\", "$"):
                raise AssertionError("Unescaped backslash in open_dir argument")
            output.append(value[index + 1])
            index += 2
        else:
            output.append(char)
            index += 1
    return "".join(output)


def simulated_expand_variables(value, variables):
    """Unit-only simulation of literal strings in the assumed escape grammar.

    This supports recursive dictionaries/lists needed by the plugin's guard.
    It does not implement or validate Sublime's actual snippet parser.
    """
    if variables != {}:
        raise AssertionError("The literal roundtrip must use an empty variable map")
    if isinstance(value, dict):
        return {key: simulated_expand_variables(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [simulated_expand_variables(item, variables) for item in value]
    if isinstance(value, str):
        return decode_literal_argument(value)
    return value


class WindowCommand:
    def __init__(self, window):
        self.window = window


class FakeSheet:
    """Both image and text tabs are sheets; an image has no text view."""

    def __init__(self, file_name, window, image=False, dirty=False):
        self.path = file_name
        self.owner = window
        self.image = image
        self.dirty = dirty

    def file_name(self):
        return self.path

    def window(self):
        return self.owner

    def view(self):
        if self.image:
            return None
        raise AssertionError("Resolve tabs from sheets, without consulting a text view")


class FakeWindow:
    def __init__(self):
        self.groups = []
        self.commands = []
        self.messages = []
        self.query_groups = []

    def num_groups(self):
        return len(self.groups)

    def sheets_in_group(self, group):
        self.query_groups.append(group)
        return self.groups[group]

    def active_view(self):
        raise AssertionError("Do not fall back to an unrelated active tab")

    def active_sheet(self):
        raise AssertionError("Do not fall back to an unrelated active tab")

    def views_in_group(self, group):
        raise AssertionError("A view list omits image and HTML sheets")

    def focus_view(self, view):
        raise AssertionError("Revealing a file must not focus or activate tabs")

    def focus_group(self, group):
        raise AssertionError("Revealing a file must not change the active group")

    def run_command(self, command, args=None):
        self.commands.append((command, args))

    def status_message(self, message):
        self.messages.append(message)


def load_plugin():
    sublime_stub = types.ModuleType("sublime")
    sublime_stub.status_message = lambda message: None
    sublime_stub.version = lambda: "4215"
    sublime_stub.platform = lambda: "linux"
    sublime_stub.expand_variables = simulated_expand_variables
    plugin_stub = types.ModuleType("sublime_plugin")
    plugin_stub.WindowCommand = WindowCommand
    spec = importlib.util.spec_from_file_location("reveal_default_explorer_under_test", PLUGIN_FILE)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"sublime": sublime_stub, "sublime_plugin": plugin_stub}):
        spec.loader.exec_module(module)
    return module, sublime_stub


class RevealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin, cls.sublime = load_plugin()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="reveal-plugin-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.active_file = self.make_file("active.txt", "active buffer on disk")
        self.clicked_file = self.make_file("clicked inactive.txt", "clicked buffer on disk")
        self.second_group_file = self.make_file("第二组 文件.txt", "second group on disk")
        self.image_file = self.make_file("interleaved image.png", "placeholder image bytes")
        self.window = FakeWindow()
        self.window.groups = [
            [FakeSheet(self.active_file, self.window), FakeSheet(self.clicked_file, self.window)],
            [FakeSheet(self.image_file, self.window, image=True),
             FakeSheet(self.second_group_file, self.window)],
        ]
        self.messages = []
        self.sublime.status_message = self.messages.append
        self.command = self.plugin.RevealInDefaultExplorerCommand(self.window)

    def make_file(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def assert_dispatch(self, path):
        self.assertEqual(len(self.window.commands), 1)
        command, args = self.window.commands[0]
        self.assertEqual(command, "open_dir")
        self.assertEqual(set(args), {"dir", "file"})
        self.assertEqual(decode_literal_argument(args["dir"]), os.path.dirname(path))
        self.assertEqual(decode_literal_argument(args["file"]), os.path.basename(path))

    def assert_no_dispatch(self, group=-1, index=-1):
        self.assertFalse(self.command.is_enabled(group=group, index=index))
        self.command.run(group=group, index=index)
        self.assertEqual(self.window.commands, [])

    def test_tab_menu_entry_has_context_placeholders(self):
        menu = json.loads((PROJECT_ROOT / "RevealInDefaultExplorer" /
                           "Tab Context.sublime-menu").read_text(encoding="utf-8"))
        entries = [entry for entry in menu
                   if entry.get("command") == "reveal_in_default_explorer"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["caption"], "Open in Explorer")
        self.assertEqual(entries[0]["args"], {"group": -1, "index": -1})

    def test_inactive_clicked_tab_is_revealed(self):
        self.assertTrue(self.command.is_enabled(group=0, index=1))
        self.command.run(group=0, index=1)
        self.assert_dispatch(self.clicked_file)

    def test_clicked_tab_in_other_group_is_revealed(self):
        self.assertTrue(self.command.is_enabled(group=1, index=1))
        self.command.run(group=1, index=1)
        self.assert_dispatch(self.second_group_file)

    def test_image_sheet_before_text_does_not_shift_clicked_index(self):
        self.command.run(group=1, index=1)
        self.assert_dispatch(self.second_group_file)

    def test_saved_image_sheet_can_be_revealed(self):
        self.assertTrue(self.command.is_enabled(group=1, index=0))
        self.command.run(group=1, index=0)
        self.assert_dispatch(self.image_file)

    def test_dirty_saved_buffer_reveals_disk_file_without_saving(self):
        self.window.groups[0][1].dirty = True
        before = Path(self.clicked_file).read_bytes()
        self.command.run(group=0, index=1)
        self.assert_dispatch(self.clicked_file)
        self.assertEqual(Path(self.clicked_file).read_bytes(), before)

    def test_untitled_buffer_is_disabled(self):
        self.window.groups[0][1].path = None
        self.assert_no_dispatch(0, 1)

    def test_empty_file_name_is_disabled(self):
        self.window.groups[0][1].path = ""
        self.assert_no_dispatch(0, 1)

    def test_missing_file_is_disabled_and_not_created(self):
        missing = self.root / "not created.txt"
        self.window.groups[0][1].path = str(missing)
        self.assert_no_dispatch(0, 1)
        self.assertFalse(missing.exists())

    def test_directory_path_is_disabled(self):
        self.window.groups[0][1].path = str(self.root)
        self.assert_no_dispatch(0, 1)

    def test_deleted_after_menu_enable_is_rechecked(self):
        self.assertTrue(self.command.is_enabled(group=0, index=1))
        Path(self.clicked_file).unlink()
        self.command.run(group=0, index=1)
        self.assertEqual(self.window.commands, [])
        self.assertFalse(Path(self.clicked_file).exists())

    def test_missing_parent_is_disabled_without_creating_it(self):
        missing = self.root / "missing parent" / "file.txt"
        self.window.groups[0][1].path = str(missing)
        self.assert_no_dispatch(0, 1)
        self.assertFalse(missing.parent.exists())

    def test_default_sentinels_do_not_use_python_negative_indexing(self):
        self.assertFalse(self.command.is_enabled())
        self.command.run()
        self.assertEqual(self.window.commands, [])
        self.assertEqual(self.window.query_groups, [])

    def test_invalid_indices_never_fall_back_to_active_tab(self):
        cases = [(-1, 0), (0, -1), (-2, 0), (0, -2), (20, 0), (0, 20)]
        for group, index in cases:
            with self.subTest(group=group, index=index):
                self.assert_no_dispatch(group, index)

    def test_non_integer_and_boolean_indices_are_rejected(self):
        for value in (None, "0", 0.0, True, False, [], {}):
            for group, index in ((value, 0), (0, value)):
                with self.subTest(group=group, index=index):
                    self.assert_no_dispatch(group, index)

    def test_empty_group_is_disabled(self):
        self.window.groups.append([])
        self.assert_no_dispatch(2, 0)

    def test_closed_or_foreign_sheet_is_disabled(self):
        for owner in (None, FakeWindow()):
            with self.subTest(owner=owner):
                self.window.groups[0][1].owner = owner
                self.assert_no_dispatch(0, 1)

    def test_access_denied_and_stat_errors_are_handled(self):
        for error in (PermissionError("access denied"), OSError("device unavailable")):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(self.plugin.os.path, "isfile", side_effect=error):
                    self.assert_no_dispatch(0, 1)

    def test_invalid_file_name_is_handled(self):
        for value in (123, [], {}, "invalid\x00path"):
            with self.subTest(file_name=value):
                self.window.groups[0][1].path = value
                self.assert_no_dispatch(0, 1)

    def test_relative_file_name_is_disabled(self):
        self.window.groups[0][1].path = "relative.txt"
        self.assert_no_dispatch(0, 1)

    def test_sheet_lookup_failure_is_handled(self):
        with mock.patch.object(self.window, "sheets_in_group", side_effect=RuntimeError("closed")):
            self.assert_no_dispatch(0, 1)

    def test_closed_sheet_file_name_failure_is_handled(self):
        with mock.patch.object(self.window.groups[0][1], "file_name", side_effect=RuntimeError("closed")):
            self.assert_no_dispatch(0, 1)

    def test_spaces_unicode_and_shell_characters_are_data(self):
        path = self.make_file("中文 space ';$(do-not-run)&[x].txt", "disk content")
        self.window.groups[0][1].path = path
        before_names = sorted(p.name for p in self.root.iterdir())
        before_contents = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with mock.patch("builtins.open", side_effect=AssertionError("No file content access")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("No shell or process invocation")):
            self.assertTrue(self.command.is_enabled(group=0, index=1))
            self.command.run(group=0, index=1)
        self.assert_dispatch(path)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), before_names)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before_contents)

    def test_windows_drive_and_unc_paths_preserve_exact_components(self):
        paths = [
            r"C:\Users\Example\中文 folder\space & quote' $file.txt",
            r"\\server\share name\文件夹\报告 [1] & final.txt",
            r"C:\$file_path\${folder}\$file_name ${file}.txt",
            r"\\server\share name\$file_name ${file}.txt",
            r"C:\$file_name.txt",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.window.commands.clear()
                self.window.groups[0][1].path = path
                with mock.patch.object(self.plugin, "os", types.SimpleNamespace(path=ntpath)), \
                        mock.patch.object(ntpath, "isfile", return_value=True):
                    self.assertTrue(self.command.is_enabled(group=0, index=1))
                    self.command.run(group=0, index=1)
                self.assertEqual(len(self.window.commands), 1)
                command, args = self.window.commands[0]
                self.assertEqual(command, "open_dir")
                self.assertEqual(set(args), {"dir", "file"})
                self.assertEqual(decode_literal_argument(args["dir"]), ntpath.dirname(path))
                self.assertEqual(decode_literal_argument(args["file"]), ntpath.basename(path))

    def test_snippet_variable_names_in_directory_and_file_are_literal(self):
        folder = self.root / "$file_path ${folder} \\$file_path"
        folder.mkdir()
        path = folder / "$file_name ${file} \\$file_name.txt"
        path.write_text("literal names on disk", encoding="utf-8")
        self.window.groups[0][1].path = str(path)
        self.assertTrue(self.command.is_enabled(group=0, index=1))
        self.command.run(group=0, index=1)
        self.assert_dispatch(str(path))
        self.assertEqual(path.read_text(encoding="utf-8"), "literal names on disk")

    def test_open_dir_failure_reports_status(self):
        with mock.patch.object(self.window, "run_command", side_effect=RuntimeError("manager unavailable")):
            self.command.run(group=0, index=1)
        self.assertEqual(self.window.commands, [])
        self.assertTrue(self.messages or self.window.messages, "Dispatch errors should give feedback")

    def test_editor_expansion_mismatch_blocks_dispatch_with_status(self):
        raw_args = {"dir": os.path.dirname(self.clicked_file), "file": os.path.basename(self.clicked_file)}
        for changed_component in ("dir", "file"):
            with self.subTest(changed_component=changed_component):
                expanded = dict(raw_args)
                expanded[changed_component] = "different literal path"
                self.messages.clear()
                self.window.messages.clear()
                with mock.patch.object(self.sublime, "expand_variables", return_value=expanded) as expand:
                    self.command.run(group=0, index=1)
                expand.assert_called_once()
                self.assertEqual(expand.call_args.args[1], {})
                self.assertEqual(self.window.commands, [])
                self.assertTrue(self.messages or self.window.messages, "Mismatch should give feedback")

    def test_editor_expansion_runtime_error_blocks_dispatch_with_status(self):
        with mock.patch.object(self.sublime, "expand_variables", side_effect=RuntimeError("parser unavailable")):
            self.command.run(group=0, index=1)
        self.assertEqual(self.window.commands, [])
        self.assertTrue(self.messages or self.window.messages, "Expansion errors should give feedback")


if __name__ == "__main__":
    unittest.main(verbosity=2)
