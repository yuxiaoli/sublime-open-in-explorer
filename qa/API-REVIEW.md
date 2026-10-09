# Sublime API and menu review

Reviewed 2026-10-07 UTC for the independent package whose requested tab menu caption is **Open in Explorer**.

## Current official API and package conventions

- [Official Menus documentation](https://www.sublimetext.com/docs/menus.html) identifies `Tab Context.sublime-menu` as the file-tab context menu, accepts JSON arrays of menu entries, and defines `command`, `caption`, and structured `args`. It does **not** document the special `group` / `index` substitution.
- [Official API Reference](https://www.sublimetext.com/docs/api_reference.html) defines a `Sheet` as a tab, potentially containing text, an image, or HTML. `Window.sheets_in_group(group)` supplies the sheets for a group. `Sheet.file_name()` is available from build 4088. Use sheets rather than `views_in_group` for tab indexing: filtering out non-text sheets could select a different tab. `WindowCommand` is attached to one window; `is_enabled` and `run` receive command arguments as keyword arguments.
- [Official API Environments](https://www.sublimetext.com/docs/api_environments.html) supports `.python-version` containing `3.8` from build 4050. Current builds map that value to Python 3.14 for backward compatibility. A `3.8` selector therefore spans older Sublime Text 4 and current releases without depending on the deprecated Python 3.3 host.
- [Official download/changelog](https://www.sublimetext.com/download) lists stable build **4215**, released **2026-09-25**. [Build 4213 announcement](https://www.sublimetext.com/blog/articles/sublime-text-4213) confirms that the new host is Python 3.14 and Python 3.3 is disabled by default.

## Clicked-tab targeting: evidence and boundary

- [Original plugin author's forum example, 2018](https://forum.sublimetext.com/t/opening-a-files-location-under-tab-context/40002/2), by kingkeith, explicitly describes `group` / `index` being populated with the location of the tab that opened the menu. The demonstrated menu uses both sentinels `-1`, and the original requester reports that the solution worked. This is primary evidence of observed runtime behavior, not an official API promise.
- [Sublime creator jps's forum explanation](https://forum.sublimetext.com/t/shortcut-to-close-other-tabs/1056/3) confirms that tab context commands act on the tab under the pointer rather than the tab with input focus. That older discussion predates current JSON menu examples and does not establish current sentinel substitution on its own.
- Recommended command behavior: require resolved, nonnegative integer `group` and `index`, validate group and sheet bounds, then obtain that sheet's path. Reject unresolved `-1` values; do not let Python negative indexing reveal the last tab, and do not silently select the active tab. Recheck disk existence at execution time. An untitled, deleted, or inaccessible file can remain disabled with a graceful status message if invoked directly.

**Not established here:** current-build native menu substitution has not been exercised in a real editor. The official shipped Default package could not be downloaded in this cloud environment. Unit-test stubs cannot prove menu substitution, GUI selection, or Windows Explorer acceptance.

## Built-in reveal command and literal paths

- [Sublime creator jps's command example](https://forum.sublimetext.com/t/way-to-add-a-keyboard-shortcut-for-reveal-in-finder/1739/6) identifies `open_dir` with `dir` and `file` as the built-in command behind Reveal in Finder / Open Containing Folder. A concrete parent directory and basename remove the need to focus the clicked tab or substitute the active view's variables.
- The command supports variable syntax; raw literal dollar signs therefore require care. [Primary console experiment by kingkeith](https://forum.sublimetext.com/t/open-containing-folder-fails-when-file-name-contains/25420/2) creates a Windows file containing `$`, compares raw and escaped `file` arguments to `open_dir`, and reports that prefixing the dollar sign with a backslash works. This directly tests `open_dir`, although it is historical evidence from Sublime Text 3.
- [Official API Reference](https://www.sublimetext.com/docs/api_reference.html#sublime.expand_variables) says `expand_variables` uses snippet syntax. [Official snippet Escaping documentation](https://www.sublimetext.com/docs/completions.html#escaping) directly defines `\$` for literal dollars. [Official build-system Variables documentation](https://www.sublimetext.com/docs/build_systems.html#variables) connects custom expansion to `expand_variables` and `extract_variables`. These sections are not a complete current `open_dir` specification; neither explicitly specifies the literal-backslash escape.
- Recommended literal encoding before dispatch: escape original backslashes first, then dollars. This is snippet escaping, not shell quoting. A roundtrip using Sublime's actual `expand_variables` against the window's variables can verify that the escaped string reconstructs the original path. Runtime QA should include Windows separators / UNC, a directory ending in a literal backslash on POSIX, `$file_path` and `${file_name}` as literal names, spaces, Unicode, and shell punctuation. Avoid launching a shell or composing a command line.

**Remaining evidence limit:** no current official documentation specifies every `open_dir` expansion rule or guarantees it is identical to `sublime.expand_variables`. Doubling literal backslashes is the conventional snippet encoding, but the current docs do not explicitly specify that rule. An actual `sublime.expand_variables(escaped, {}) == original` roundtrip can fail closed if this assumption is wrong on the installed editor. The raw-dollar problem is avoidable; an escaped implementation plus native QA should be used when a legitimate editor becomes available.

## OS default file manager versus Explorer replacement

[Official tracker issue 5458](https://github.com/sublimehq/sublime_text/issues/5458) was read with all comments through the authorized GitHub read connector; its web-rendered summary omitted an important partial fix:

- [Maintainer Benjamin Schaaf's comment](https://github.com/sublimehq/sublime_text/issues/5458#issuecomment-1247651398) identifies build **4135** as fixing the file-reveal case.
- [Original reporter's follow-up](https://github.com/sublimehq/sublime_text/issues/5458#issuecomment-1310767124) confirms Open Containing Folder then reached their Explorer replacement, while Browse Packages still opened standard Explorer.
- [Maintainer's later comment](https://github.com/sublimehq/sublime_text/issues/5458#issuecomment-1311085120) confirms the distinction between revealing a selected file and merely opening a directory, and reopens the latter issue.

Consequently, do not claim the current built-in file-reveal command always bypasses Explorer replacements. Delegate selection to Sublime / the OS, recommend build 4135+ where replacement hooks matter, and state that third-party replacements depend on their OS integration. Standard Windows Explorer is the expected Windows acceptance target; this cloud review is not its GUI acceptance test.

## Cloud download blocker

The [official published Linux archive](https://www.sublimetext.com/download_thanks?target=x64-tar) resolves to `https://download.sublimetext.com/sublime_text_build_4215_x64.tar.xz`.

- `curl --fail --location` to **download.sublimetext.com** returned **HTTP 403** with default sandbox permissions, explicit additional network permission, and a sandbox escalation. The escalation command ran; this was not an automatic approval-review rejection.
- The web tool could open the official download page but rejected the archive with **400 Unsupported content-type: application/octet-stream**.
- Shell access to **www.sublimetext.com** also returned **proxy CONNECT 403**.
- No proxy bypass or unofficial binary mirror was used. The [official source repository](https://github.com/sublimehq/Packages#missing-packages) explicitly excludes `Default`, so its public syntax packages cannot supply the needed shipped menu.

This limits real-editor QA and shipped-Default inspection until a legitimately available editor or authorized official archive is accessible. All implementation and mock-test claims must preserve that boundary.
