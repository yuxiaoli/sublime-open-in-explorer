"""Install the plugin's source files into Sublime Text 4's Packages directory."""

import argparse
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "RevealInDefaultExplorer"
PACKAGE_FILES = (
    ".python-version",
    "RevealInDefaultExplorer.py",
    "Tab Context.sublime-menu",
)


def default_packages_dir():
    """Return the standard per-user ST4 location; portable installs need an override."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise ValueError("APPDATA is unset; specify --packages-dir.")
        data_dir = Path(appdata) / "Sublime Text"
    elif sys.platform == "darwin":
        data_dir = Path.home() / "Library" / "Application Support" / "Sublime Text"
    elif sys.platform.startswith("linux"):
        config_home = os.environ.get("XDG_CONFIG_HOME")
        data_dir = (Path(config_home) if config_home else Path.home() / ".config") / "sublime-text"
    else:
        raise ValueError("Unsupported platform; specify --packages-dir.")
    return data_dir / "Packages"


def install(packages_dir, dry_run=False):
    """Copy only runtime files, updating existing copies without deleting other files."""
    packages_dir = Path(os.path.expandvars(str(packages_dir))).expanduser().resolve()
    source = ROOT / PACKAGE_NAME
    destination = packages_dir / PACKAGE_NAME
    if destination.resolve() == source.resolve():
        raise ValueError("The installation destination is the source directory.")

    archive = packages_dir.parent / "Installed Packages" / (PACKAGE_NAME + ".sublime-package")
    if archive.exists():
        raise ValueError(
            "A packaged installation already exists at {}. Remove it before "
            "installing from source.".format(archive)
        )

    # Validate every file before creating directories or updating an installation.
    for name in PACKAGE_FILES:
        if not (source / name).is_file():
            raise FileNotFoundError("Required plugin file is missing: {}".format(source / name))
        target = destination / name
        if target.exists() and not target.is_file():
            raise ValueError("Installation target is not a file: {}".format(target))

    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    for name in PACKAGE_FILES:
        target = destination / name
        if dry_run:
            print("Would copy {} -> {}".format(source / name, target))
        else:
            shutil.copy2(source / name, target)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packages-dir", type=Path,
        help="Packages directory shown by Preferences > Browse Packages "
             "(use this for portable or custom installations)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show copies without writing files")
    args = parser.parse_args(argv)
    try:
        packages_dir = args.packages_dir if args.packages_dir is not None else default_packages_dir()
        destination = install(packages_dir, dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        print("Installation failed: {}".format(error), file=sys.stderr)
        return 1
    if args.dry_run:
        print("Dry run complete; no files were written.")
    else:
        print("Installed {} to {}".format(PACKAGE_NAME, destination))
        print("Restart Sublime Text to load the plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
