# Actual editor and Windows acceptance checklist

Status for this delivery: **not run**. Stub tests cannot validate native menu argument substitution, the editor's variable expansion, launching a manager, or Explorer selection. Use a disposable Sublime profile and files you own. This checklist does not authorize installing on anyone else's device.

1. Install the `.sublime-package` in an ST4 build 4088+ profile. Restart. Check the Sublime console for load errors. Confirm the tab context menu has exactly one item labeled **Open in Explorer**.
2. Save `active.txt` and `中文 inactive file.txt` in different directories. Keep the first active; right-click the second tab. Invoke the item and verify the second file is selected in Windows Explorer. Verify the editor still has the same active tab.
3. Split into two groups. Put an image tab before a text tab in group 2; keep group 1 active. Right-click the later text tab in group 2 and verify its file, then repeat for the image tab. This checks native group/index substitution and sheet ordering.
4. Use an untitled buffer containing unsaved text. Confirm the item is visible but disabled. Edit an already saved file without saving; invoke the item and verify the disk content is unchanged.
5. Delete a disposable test file outside Sublime while its buffer remains open. Confirm the item becomes disabled, creates nothing and leaves the buffer intact. Also exercise an unavailable parent/share. If the file disappears after the menu was enabled, execution must stop gracefully.
6. Test spaces, Chinese/Unicode, apostrophes, `&`, literal `$file_name`, `${file}`, and a folder named `$file_path`. On Windows also test a drive root and an authorized UNC share. Confirm the exact intended file is selected and no unrelated path is opened. On POSIX additionally test a literal backslash filename.
7. If using an Explorer replacement, record the Windows version, ST build and replacement version. Verify selection there separately. Compare Sublime's standard Open Containing Folder on the same path; replacement integration depends on native OS hooks.
8. Repeat applicable cases on macOS/Linux. Record whether native integration selects the file or only opens its directory. Avoid calling this Windows Explorer acceptance.
9. Remove the installed package, restart, and confirm the item disappears.

Record build, OS, runtime, menu label, expected/actual selected path, pass/fail, and screenshot or observed GUI evidence. Keep this separate from the stub test log. Programmatic `window.run_command("reveal_in_default_explorer", {"group": 1, "index": 1})` alone does not validate a real right-click event.
