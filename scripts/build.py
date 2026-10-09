"""Build deterministic, dependency-free installation and source archives."""

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "1.0.0"
STAMP = (2026, 10, 7, 0, 0, 0)


def archive(output, entries):
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as bundle:
        for path, name in sorted(entries, key=lambda item: item[1]):
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(output) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("Archive integrity check failed: " + output.name)


def main():
    DIST.mkdir(exist_ok=True)
    package_files = [
        (ROOT / "RevealInDefaultExplorer" / name, name)
        for name in (".python-version", "RevealInDefaultExplorer.py",
                     "Tab Context.sublime-menu")
    ] + [(ROOT / name, name) for name in ("README.md", "LICENSE")]
    package = DIST / "RevealInDefaultExplorer.sublime-package"
    archive(package, package_files)

    source_files = [ROOT / name for name in (".gitignore", "README.md", "LICENSE")]
    for directory in ("RevealInDefaultExplorer", "tests", "scripts", "qa"):
        source_files.extend(
            path for path in (ROOT / directory).rglob("*")
            if path.is_file() and not any(
                part in ("__pycache__", "runtime") for part in path.relative_to(ROOT).parts
            ) and path.suffix not in (".pyc", ".pyo")
        )
    source = DIST / ("sublime-reveal-default-explorer-source-" + VERSION + ".zip")
    archive(source, [(path, "sublime-reveal-default-explorer/" +
                      path.relative_to(ROOT).as_posix()) for path in source_files])

    artifacts = []
    for path in (package, source):
        artifacts.append({
            "filename": path.name,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    (DIST / "SHA256SUMS").write_text("".join(
        item["sha256"] + "  " + item["filename"] + "\n" for item in artifacts
    ), encoding="utf-8")
    manifest = {"version": VERSION, "artifacts": artifacts}
    (DIST / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
