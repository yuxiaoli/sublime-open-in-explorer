#!/usr/bin/env python3
"""Install RevealInDefaultExplorer into a Sublime Text 4 Installed Packages directory."""

import argparse
import io
import os
from pathlib import Path
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "RevealInDefaultExplorer.sublime-package"
SOURCE_FILES = (
    ("RevealInDefaultExplorer/.python-version", ".python-version"),
    ("RevealInDefaultExplorer/RevealInDefaultExplorer.py", "RevealInDefaultExplorer.py"),
    ("RevealInDefaultExplorer/Tab Context.sublime-menu", "Tab Context.sublime-menu"),
    ("README.md", "README.md"),
    ("LICENSE", "LICENSE"),
)
STAMP = (2026, 10, 7, 0, 0, 0)


class InstallError(Exception):
    """An unsafe or unavailable installation destination."""


def build_package(root):
    """Match build.py's deterministic, explicit five-file installation payload."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as bundle:
        for relative, name in sorted(SOURCE_FILES, key=lambda item: item[1]):
            source = root / relative
            if source.is_symlink() or not source.is_file():
                raise InstallError("Required source file is missing or unsafe: " + str(source))
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, source.read_bytes(), compresslevel=9)
    return output.getvalue()


def default_data_roots(platform=None, environ=None, home=None):
    """Only current ST4 defaults; portable/custom profiles require --target."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform == "win32":
        appdata = environ.get("APPDATA")
        if not appdata:
            return []
        base = Path(appdata)
        if not base.is_absolute():
            raise InstallError("APPDATA must be an absolute path; use --target instead.")
        return [base / "Sublime Text"]
    if platform == "darwin":
        return [home / "Library" / "Application Support" / "Sublime Text"]
    if platform.startswith("linux"):
        base = Path(environ.get("XDG_CONFIG_HOME") or home / ".config")
        if not base.is_absolute():
            raise InstallError("XDG_CONFIG_HOME must be an absolute path; use --target instead.")
        return [base / "sublime-text"]
    raise InstallError("Unsupported platform; specify an explicit --target directory.")


def discover_target():
    candidates = [root for root in default_data_roots() if root.is_dir()]
    if not candidates:
        raise InstallError("No existing Sublime Text 4 data directory found; use --target.")
    if len(candidates) != 1:
        raise InstallError("Multiple Sublime data directories found; choose one with --target.")
    return candidates[0] / "Installed Packages"


def validate_target(target):
    target = Path(target).expanduser().absolute()
    if target.name != "Installed Packages":
        raise InstallError("--target must name the exact 'Installed Packages' directory.")
    if target.is_symlink() or target.parent.is_symlink():
        raise InstallError("Refusing a symlink destination or data directory: " + str(target))
    if target.exists() and not target.is_dir():
        raise InstallError("Installation target is not a directory: " + str(target))
    if not target.parent.is_dir():
        raise InstallError("The target's parent data directory must already exist: " +
                           str(target.parent))
    unpacked = target.parent / "Packages" / "RevealInDefaultExplorer"
    if unpacked.exists() or unpacked.is_symlink():
        raise InstallError("An unpacked plugin already exists at " + str(unpacked) +
                           "; remove or move it before installing the packaged version.")
    package = target / PACKAGE_NAME
    if package.is_symlink() or (package.exists() and not package.is_file()):
        raise InstallError("Refusing an unsafe existing package: " + str(package))
    return target


def write_temporary(target, payload, suffix):
    """Create an exclusive file and flush it before any replacement."""
    descriptor, name = tempfile.mkstemp(prefix=PACKAGE_NAME + ".", suffix=suffix,
                                       dir=str(target))
    path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink()
        raise
    return path


def write_new_package(package, payload):
    """Portable first-install fallback: create exclusively, never truncate."""
    try:
        stream = package.open("xb")
    except FileExistsError as error:
        raise InstallError("A package appeared during installation; it was not replaced.") from error
    created = None
    try:
        with stream:
            created = os.fstat(stream.fileno())
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as error:
        # Remove our incomplete file only if nobody has replaced it meanwhile.
        if created is not None and created.st_ino:
            try:
                if os.path.samestat(created, package.lstat()):
                    package.unlink()
            except FileNotFoundError:
                pass
        if isinstance(error, OSError):
            raise InstallError("First installation could not be completed: " + str(error) +
                               ". Inspect " + str(package) + " before retrying.") from error
        raise


def install(root, target, dry_run=False, update=False):
    payload = build_package(Path(root))
    target = validate_target(target)
    package = target / PACKAGE_NAME
    previous = package.read_bytes() if package.exists() else None
    if previous == payload:
        return "Already up to date: " + str(package)
    if previous is not None and not update:
        raise InstallError("A different package already exists at " + str(package) +
                           "; review it and rerun with --update to keep a backup and replace it.")
    if dry_run:
        action = "back up and replace" if previous is not None else "install"
        return "Dry run: would " + action + " " + str(package) + ". No files changed."

    target.mkdir(exist_ok=True)
    temporary = write_temporary(target, payload, ".tmp")
    backup = None
    try:
        # Recheck after preparing the new archive, avoiding stale update decisions.
        validate_target(target)
        current = package.read_bytes() if package.exists() else None
        if current != previous:
            raise InstallError("The package changed during installation; rerun after reviewing it.")
        if previous is not None:
            backup = write_temporary(target, previous, ".bak")
            validate_target(target)
            if not package.exists() or package.read_bytes() != previous:
                raise InstallError("The package changed while backing it up; rerun after reviewing it.")
            os.replace(str(temporary), str(package))
        else:
            # Linking publishes the complete file exclusively: an arriving package
            # must never be overwritten by a first installation.
            try:
                os.link(str(temporary), str(package))
            except FileExistsError as error:
                raise InstallError("A package appeared during installation; it was not replaced.") from error
            except OSError:
                # Some portable/network filesystems do not support hard links.
                # xb still refuses any existing file; keep the editor closed
                # until this non-atomic first-install fallback finishes.
                write_new_package(package, payload)
    finally:
        if temporary.exists():
            temporary.unlink()
    message = "Installed: " + str(package)
    if backup is not None:
        message += "\nPrevious package backed up to: " + str(backup)
    return message + "\nRestart Sublime Text to load the package."


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, metavar="PATH",
                        help="exact Installed Packages directory; parent must already exist")
    parser.add_argument("--dry-run", action="store_true", help="validate and preview without writes")
    parser.add_argument("--update", action="store_true",
                        help="back up and replace a different existing package")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 8):
        parser.error("Python 3.8 or later is required.")
    try:
        target = args.target if args.target is not None else discover_target()
        print(install(ROOT, target, dry_run=args.dry_run, update=args.update))
    except (InstallError, OSError) as error:
        parser.exit(1, "Error: " + str(error) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
