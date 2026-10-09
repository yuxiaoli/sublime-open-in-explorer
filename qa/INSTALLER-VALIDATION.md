# Installer validation — 2026-10-09 UTC

The installer and English README were prepared on `develop`. No installation into a live Sublime profile was performed during validation.

## Automated checks

- **58 tests passed** on cloud Linux with CPython 3.12.14: 30 installer tests and the existing 28 plugin tests.
- Installer tests perform actual file operations only in isolated temporary directories, including paths with spaces and Unicode.
- Coverage includes first installation, identical repeat installs, explicit update permission, unique inactive backups, dry runs without directory creation or file changes, missing sources and parents, invalid targets, duplicate unpacked installations, symlinks, and preservation of unrelated packages and user settings.
- Failure cases cover writing/flushing a temporary archive, creating a backup, replacing the installed archive, and a package appearing or changing during installation. When hard links are unavailable, first installation falls back to exclusive file creation without overwriting an existing package.
- The portability checks verify that hard links use a temporary sibling in the target directory, that first installation succeeds when hard links are unavailable, and that exclusive-create write/flush/fsync failures clean up only a partial file with a matching nonzero file identity. Concurrent replacements and files with unavailable identity are preserved; failed installation reports the path to inspect.
- The install archive contains exactly `.python-version`, `RevealInDefaultExplorer.py`, `Tab Context.sublime-menu`, `README.md`, and `LICENSE`. Tests verify byte equality with `scripts/build.py`; additional tests, Git files, secrets, and bytecode are excluded from this install payload.
- Windows and macOS discovery rules are checked with mocked platform inputs on Linux. They are not native Windows/macOS execution tests.
- An end-to-end CLI smoke check passed against a temporary target with spaces and Unicode: dry-run, first install, identical repeat, refused overwrite, update dry-run, and an update preserving the old archive in a backup.
- The new installer and test files pass Python 3.8 syntax parsing. Execution used Python 3.12.14; this is not a separate Python 3.8 runtime test.

## Reproduce

Run from the source project root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/install.py --help
python3 scripts/build.py
```

For installation commands, prerequisites, backup behavior, and portable/custom targets, see `README.md`. Temporary files are siblings of the destination archive; the source checkout may be on another volume. Hard links are optional. The exclusive-create first-install fallback is not atomic, so keep the editor closed until installation completes; an abrupt process termination may leave an incomplete new archive. Updates still back up and atomically replace the existing archive.

## Remaining verification

No actual Sublime or Windows Explorer GUI acceptance was performed. The earlier official editor download denial was not retried. The manual steps in `qa/EDITOR_QA.md` remain outstanding.
