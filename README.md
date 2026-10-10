# Open in Explorer — RevealInDefaultExplorer

An independent Sublime Text 4 plugin with no third-party dependencies. Right-click a tab and select **Open in Explorer** to reveal that tab's file in the file manager. The menu label is exactly `Open in Explorer`, including capitalization and spaces.

## Installation

Choose one of the following installation methods. Avoid installing both the packaged and unpacked versions.

### Install the `.sublime-package`

1. Download the supplied `RevealInDefaultExplorer.sublime-package` file. Keep its filename and do not extract it.
2. In Sublime Text, choose **Preferences → Browse Packages…** to open the `Packages` directory.
3. Go up one level to Sublime's data directory. Open or create the adjacent `Installed Packages` directory, then copy the file into it.
4. Restart Sublime Text.

A standard Windows installation normally uses `%APPDATA%\Sublime Text\Installed Packages`. A portable installation uses `Data\Installed Packages` alongside the editor. Use **Browse Packages** to locate the active instance's data directory so that you do not install the plugin into another version's directory.

### Install from source

Run this command from the source project root (requires a local Python 3 installation):

```sh
python scripts/install.py
```

The script copies the three runtime files, including the hidden `.python-version` file, into the current user's default Sublime Text 4 `Packages/RevealInDefaultExplorer` directory. Running it again updates those three files and preserves other files in that directory. Add `--dry-run` to preview the destination without writing any files.

For a portable installation or custom data directory, use **Preferences → Browse Packages…** to locate the active instance's `Packages` directory, then specify it explicitly:

```sh
python scripts/install.py --packages-dir "D:/Sublime Text/Data/Packages"
```

Restart the editor after installation. If `Installed Packages/RevealInDefaultExplorer.sublime-package` already exists in the same data directory, the script reports an error. Remove that package before running the script to avoid a mixed installation.

You can also install manually:

1. Extract `sublime-reveal-default-explorer-source-1.0.0.zip`.
2. Choose **Preferences → Browse Packages…** to open the `Packages` directory.
3. Copy only the source archive's `RevealInDefaultExplorer` folder into that directory.
4. Confirm that `Packages/RevealInDefaultExplorer/RevealInDefaultExplorer.py` exists, with `Tab Context.sublime-menu` and the hidden `.python-version` file in the same folder. Then restart the editor.

Do not copy the entire source project or its test directory into `Packages`. The plugin itself does not require Package Control, an API key, or a separate Python installation; only the optional installer script requires local Python.

## Usage and limitations

- Right-click the tab you want to reveal and select **Open in Explorer**. The command uses the clicked tab, including inactive tabs and tabs in other groups; you do not need to activate it first.
- For a saved file with unsaved changes, the command reveals the existing file on disk without saving the buffer.
- The menu item is disabled for untitled buffers or buffers without a file on disk, missing or deleted files, and inaccessible paths. If the file disappears after the menu opens, the command stops and displays a status-bar message.
- Image tabs can also be revealed. HTML and other tabs without an associated file on disk are disabled.
- Spaces, Unicode, UNC paths, `$`, and backslashes are treated as part of the path; paths are never assembled into shell commands. Symbolic links retain the path shown in the tab rather than being resolved to the target's path. Broken links are disabled.

The plugin passes the directory and filename to Sublime's built-in `open_dir` command. On Windows, the expected behavior is to select the file in Explorer. On macOS and Linux, it uses Sublime's file-manager integration. Whether the file is selected depends on support in the editor, operating system, and file manager; some Linux environments may only open the directory.

**The system default and third-party replacements:** The plugin follows Sublime's operating-system file-manager integration and does not specify a third-party program. In issue #5458, an official maintainer explained that selecting a file and opening only its directory use different Windows APIs. After the fix in build 4135, the reporter confirmed that revealing a file worked with their replacement file manager. Support for your Explorer replacement depends on its OS hooks; the plugin cannot guarantee compatibility with every replacement. Build 4135 or later is recommended if you need this behavior. The menu label does not change these underlying limitations. [Official issue and fix discussion](https://github.com/sublimehq/sublime_text/issues/5458#issuecomment-1311085120)

The built-in command does not return a result that lets the plugin confirm that the GUI opened or selected the file successfully. Even after the file passes validation and the command is issued, an OS-level launch failure may only appear in the Sublime console. The plugin does not display a false success message.

## Compatibility

- Requires Sublime Text 4 **build 4088 or later**, using `Sheet.file_name()`, which was introduced in build 4088. Sublime Text 2 and 3 are not supported.
- At the documentation review on 2026-10-07, the official stable release was build 4215, released on 2026-09-25. Actual runtime acceptance testing of that release has not been completed in this cloud environment. [Official download and release history](https://www.sublimetext.com/download)
- `.python-version` is set to `3.8`: earlier ST4 versions use their Python 3.8 host, while newer versions map this value to Python 3.14 for compatibility. The plugin does not depend on the deprecated Python 3.3 host. [Official Python environment documentation](https://www.sublimetext.com/docs/api_environments.html)

## Uninstallation

Close Sublime Text, delete `Installed Packages/RevealInDefaultExplorer.sublime-package` for a packaged installation or `Packages/RevealInDefaultExplorer` for a source installation, then restart the editor. If you installed both versions, remove both.

## Implementation and development validation

The plugin implementation consists of one Python module, one tab-menu file, and a Python host-selection file. The command reads the `group` and `index` supplied by the context menu and resolves the tab using `sheets_in_group`. It does not fall back to the active tab or change focus. If the editor has not replaced the `-1` placeholder arguments, the command is disabled to prevent a negative index from selecting the wrong tab. Before calling `open_dir`, it uses the installed editor's `expand_variables` to verify that the escaped arguments restore the original literal paths; if they do not, it stops and displays a message. At runtime, it only checks path existence and invokes the built-in command. It does not read file contents or write to files or the registry.

The official menu documentation confirms that `Tab Context.sublime-menu` defines the tab context menu. Details of automatic `group/index` substitution come from the original author's working example and user confirmations on the official forum; the current menu documentation does not describe these two parameters individually. The current official release package was not obtained for inspection, and the stub tests do not establish that the editor performs this substitution. [Menu documentation](https://www.sublimetext.com/docs/menus.html), [API reference](https://www.sublimetext.com/docs/api_reference.html), [Original tab-argument example](https://forum.sublimetext.com/t/opening-a-files-location-under-tab-context/40002)

Run these commands from the source project root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The build produces the installable package, a source ZIP, `SHA256SUMS`, and a manifest of file sizes and hashes. Tests use minimal Sublime stubs and the standard library's `ntpath` for Windows path handling. These tests are not equivalent to acceptance testing in the actual Sublime GUI or Windows Explorer. See `qa/VALIDATION.md` for detailed evidence and `qa/EDITOR_QA.md` for the manual Windows checks.

## Quick start

Copy `RevealInDefaultExplorer.sublime-package` into the active Sublime data directory's `Installed Packages`, then restart. Right-click the file tab and select **Open in Explorer**. The clicked tab is resolved even when inactive or in another group. Buffers without a file on disk and missing files are disabled. Existing dirty buffers are not saved. Requires ST4 build 4088+; build 4135+ is recommended for Windows replacement-manager integration. Actual file-manager selection depends on Sublime and OS support. Remove the installed package to uninstall.
