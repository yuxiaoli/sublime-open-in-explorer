# Validation

## Open in Terminal — 2026-10-10 (Asia/Shanghai)

- **42 automated tests pass** on Windows with bundled CPython 3.12: the 28 Explorer tests and 14 new Terminal tests. The existing literal-name fixture now uses backslashes as filename characters only on POSIX; its Windows case still checks literal dollar signs and snippet-like names.
- Both menu commands share the clicked-sheet and file validation. Terminal tests cover inactive/dirty tabs in another group, image tabs, disabled/invalid paths and coordinates, deletion after enablement, Unicode/spaces/punctuation, Windows drive roots and UNC paths, platform launch arguments, PowerShell fallback, unavailable terminal aliases and launch failures.
- Terminal launch uses argument lists with `shell=False`. Windows Terminal receives `-d .` with the clicked file's directory as `cwd`, so that directory never enters its command-separator parser. No file contents are executed or saved by the plugin.
- All terminal processes are mocked in these tests. Real Sublime right-click substitution, terminal window display, shell startup behavior and actual initial working directories have **not** been validated in the GUI. Manual acceptance steps are in `qa/EDITOR_QA.md`.

## Original delivery — 2026-10-07 UTC

Package version: **1.0.0**. Exact menu label: **Open in Explorer**.

## Completed

- **28 automated tests pass**, using standard-library `unittest` and minimal Sublime stubs on cloud Linux, CPython 3.12.14. The captured run is `qa/test-output.txt`.
- Coverage: right-click target coordinates for inactive tabs and multiple groups, image/text sheets without index shifts, dirty saved buffers, untitled files, empty/relative/invalid paths, missing/deleted files and parents, stat access errors, stale/foreign sheets and lookup failures, invalid/unresolved indices, Windows drive/UNC/root paths through `ntpath`, Unicode/spaces/punctuation, literal snippet variable names, path-expansion mismatches and dispatch errors.
- File operations in the plugin are read-only path checks. Tests confirm dirty-file contents are unchanged and missing paths are not created; the plugin does not call file-content access or process/shell launch APIs. The native `open_dir` command owns OS integration.
- The native `expand_variables` API is called at runtime before dispatch to verify that escaped arguments reconstruct the intended literal paths. Unit tests simulate its escape grammar and verify fail-closed behavior; they do not establish the actual native grammar.
- Official current menu/API/runtime documentation and primary forum experiments reviewed. Detailed source links, Windows replacement-manager correction and evidence limits are in `qa/API-REVIEW.md`.
- Installation archive stores the module, menu and `.python-version` at its root with README and LICENSE. Source archive contains only this independent project, documentation, build script and tests; cloud QA runtime files, bytecode, Library helpers and editor binaries are excluded.
- Archives are built with stable names, timestamps and permissions. Build checks ZIP CRC integrity; release verification compares packaged files byte-for-byte with the source and checks SHA-256 and reproducibility.

## Actual editor / Windows acceptance: NOT RUN

No Sublime Text executable was installed or available on the cloud PATH or in the checked standard application locations. A temporary isolated non-root Xorg display with a dummy driver worked at 1280×800, and was stopped after the editor download proved unavailable. Xorg availability does not constitute editor acceptance.

The officially published build 4215 Linux archive at **download.sublimetext.com** returned **HTTP 403** to cloud `curl`, including a reviewed sandbox escalation. The command ran, so this was a network denial, not an automatic approval-review rejection. Shell HTTPS to **www.sublimetext.com** returned **proxy CONNECT 403**. The web tool opened documentation but rejected the official binary with **400 Unsupported content-type: application/octet-stream**. No download mirror or bypass was used.

Therefore the current shipped Default package, native tab-menu sentinel substitution, actual native `open_dir` expansion, OS manager launch and GUI file selection were **not** tested here. The original tab-context forum example confirms historical behavior; the plugin rejects unresolved sentinel arguments instead of using an unrelated active tab. This release must not be described as real Windows Explorer GUI acceptance.

The pending acceptance steps are concrete and reproducible in `qa/EDITOR_QA.md`. Windows is the primary user target. Third-party Explorer replacements depend on Sublime/OS hooks; build 4135+ is recommended for the recorded replacement-manager fix. Linux/macOS file selection may differ.

## Scope

Implementation and generated deliverables are confined to `/workspace/sublime-reveal-default-explorer`, with Library transfer helpers in a task-specific `/tmp` directory. No installation on the user's device, GitHub repository, push, marketplace submission or registry modification was performed.

## Reproduce

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

`dist/SHA256SUMS` and `dist/artifact-manifest.json` describe the installation and source archives. Library receipt IDs are supplied separately at handoff, keeping them out of source archives.
