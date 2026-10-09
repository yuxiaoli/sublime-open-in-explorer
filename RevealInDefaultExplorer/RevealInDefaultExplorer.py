"""Reveal the file belonging to the tab that opened the context menu."""

import os

import sublime
import sublime_plugin


class RevealInDefaultExplorerCommand(sublime_plugin.WindowCommand):
    def _file_name(self, group, index):
        # Sublime substitutes these menu args with the clicked tab's location.
        # Unresolved sentinels must never become Python's negative indexing or
        # silently fall back to the active tab.
        if type(group) is not int or type(index) is not int:
            return None
        if group < 0 or index < 0:
            return None

        try:
            if group >= self.window.num_groups():
                return None
            sheets = self.window.sheets_in_group(group)
            if index >= len(sheets):
                return None
            sheet = sheets[index]
            if sheet.window() != self.window:
                return None
            # Sheets preserve tab indices when non-text tabs are present.
            path = sheet.file_name()
        except (IndexError, RuntimeError):
            # The window or tab may have closed while the menu was open.
            return None

        if not isinstance(path, str) or not path or not os.path.isabs(path):
            return None
        return path

    @staticmethod
    def _is_file(path):
        if path is None:
            return False
        try:
            return os.path.isfile(path)
        except (OSError, ValueError):
            return False

    def is_enabled(self, group=-1, index=-1):
        return self._is_file(self._file_name(group, index))

    @staticmethod
    def _literal(value):
        # open_dir expands snippet-style variables. Preserve literal backslashes
        # and dollar signs, including names such as "$file_name.txt".
        return value.replace("\\", "\\\\").replace("$", "\\$")

    def run(self, group=-1, index=-1):
        path = self._file_name(group, index)
        if path is None:
            sublime.status_message("Open in Explorer: this tab has no saved file.")
            return
        # Recheck at execution time: a file can disappear while the menu is open.
        if not self._is_file(path):
            sublime.status_message("Open in Explorer: file is missing or inaccessible.")
            return

        try:
            raw_args = {"dir": os.path.dirname(path), "file": os.path.basename(path)}
            args = {key: self._literal(value) for key, value in raw_args.items()}
            # Use the installed editor's parser to check literal roundtripping.
            # Fail closed if its escaping grammar differs from our assumptions.
            if sublime.expand_variables(args, {}) != raw_args:
                sublime.status_message("Open in Explorer: could not preserve the literal file path.")
                return
            self.window.run_command("open_dir", args)
        except (OSError, RuntimeError, ValueError):
            sublime.status_message("Open in Explorer: could not open the file manager.")
