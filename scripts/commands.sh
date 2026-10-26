# Command reference. Copy individual Bash examples from the source project root.
# Never execute/source this entire file. This is a Sublime Text GUI plugin,
# NOT a standalone file-manager CLI. No package manager/dependencies required.
# Helper scripts require Python 3.8+ outside Sublime; runtime needs ST4 build
# 4088+ (README recommends 4135+ for Windows replacement-manager integration).
# No tests/build/install/GUI operations were run to author this catalogue.

# === Development validation and deterministic local build ===
# Tests use stubs and isolated temporary files, NOT the actual Sublime GUI.
python3 -m unittest discover -s tests -v
# Build overwrites dist artifacts, but does not install or publish anything.
python3 scripts/build.py
# Outputs:
# dist/RevealInDefaultExplorer.sublime-package
# dist/sublime-reveal-default-explorer-source-1.0.0.zip
# dist/SHA256SUMS
# dist/artifact-manifest.json
# Install package contains exactly 3 runtime files plus README.md and LICENSE.
# Source ZIP recursively includes scripts/tests/qa/runtime sources (except named
# runtime/cache directories and bytecode); review that tree before distribution.
# Build has no argument parser/options: --help would still perform the build.

# === Installer help and actual no-write preview ===
python3 scripts/install.py --help
python3 scripts/install.py --dry-run
# Default discovery requires an existing ST4 data directory:
# Windows APPDATA/Sublime Text; macOS ~/Library/Application Support/Sublime Text;
# Linux XDG_CONFIG_HOME/sublime-text, otherwise ~/.config/sublime-text.
# Portable/custom: find the ACTIVE instance via Preferences > Browse Packages,
# go up to the data directory, then supply its exact Installed Packages path.
# Replace YOUR_EXISTING_SUBLIME_DATA; its parent directory must already exist.
python3 scripts/install.py --target "YOUR_EXISTING_SUBLIME_DATA/Installed Packages" --dry-run

# === Install: close Sublime first; preview and inspect target before writing ===
# Choose automatic OR explicit target, not two installations.
python3 scripts/install.py
python3 scripts/install.py --target "YOUR_EXISTING_SUBLIME_DATA/Installed Packages"
# Installer constructs payload from source, so no prebuilt archive is needed.
# Identical installed payload is a no-op. A different package requires --update.
# Target/data-directory/package symlinks and duplicate unpacked
# Packages/RevealInDefaultExplorer are refused. Keep backups outside Packages.
# First install fallback may not be atomic on filesystems without hardlinks;
# keep editor closed until completion and inspect any interrupted partial file.

# === Explicit update alternatives: unique .bak retained beside prior archive ===
python3 scripts/install.py --update --dry-run
python3 scripts/install.py --update
python3 scripts/install.py --target "YOUR_EXISTING_SUBLIME_DATA/Installed Packages" --update --dry-run
python3 scripts/install.py --target "YOUR_EXISTING_SUBLIME_DATA/Installed Packages" --update
# Restart Sublime after installing/updating. No uninstall flag is implemented.

# === Windows PowerShell equivalents (comments, NOT Bash) ===
# py -3 -m unittest discover -s tests -v
# py -3 scripts/build.py
# py -3 scripts/install.py --target "$env:APPDATA\Sublime Text\Installed Packages" --dry-run
# py -3 scripts/install.py --target "$env:APPDATA\Sublime Text\Installed Packages"
# py -3 scripts/install.py --target "$env:APPDATA\Sublime Text\Installed Packages" --update --dry-run
# py -3 scripts/install.py --target "$env:APPDATA\Sublime Text\Installed Packages" --update
# Use python instead of py -3 if the launcher is absent.

# === Manual GUI installation/use/uninstallation; no invented CLI ===
# Alternative manual package install: copy the unextracted .sublime-package into
# the active Installed Packages directory. Or copy ONLY RevealInDefaultExplorer/
# into active Packages, including .python-version; never install both forms.
# Right-click the intended file tab and choose exactly "Open in Explorer".
# It uses the clicked sheet, including inactive tabs/other groups, without saving
# dirty buffers. Untitled/missing/inaccessible files are disabled; no file content
# is read and no registry/settings changes are made by the runtime plugin.
# Actual file selection depends on Sublime and the OS/file-manager integration;
# some Linux managers may only open the directory. No GUI success confirmation.
# Manual acceptance: qa/EDITOR_QA.md covers menu argument substitution, inactive
# tabs/groups/images, Unicode/spaces/$/backslashes, dirty/untitled/missing files,
# and native Windows Explorer or replacement-manager behavior.
# Existing qa logs are historical evidence, NOT a test run of this commit.
# To uninstall: close Sublime, remove only its installed package OR unpacked
# plugin folder from the identified active profile, then restart. No blanket rm
# command is supplied to avoid removing another profile or unrelated packages.
# No automated release/upload/deployment command is defined.
