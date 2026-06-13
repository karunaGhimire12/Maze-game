"""
scripts/version_sync.py
────────────────────────────────────────────────────────────────────────────
Single-source-of-truth version manager — the Python equivalent of an npm
"version:sync" script.

The canonical version lives in the VERSION file at the project root.
Running this script will:

  1. Read the current version from VERSION (creating it with "0.1.0" if
     missing).
  2. Optionally bump it:
         python scripts/version_sync.py            -> no bump, just sync
         python scripts/version_sync.py patch      -> 1.2.3 -> 1.2.4
         python scripts/version_sync.py minor      -> 1.2.3 -> 1.3.0
         python scripts/version_sync.py major      -> 1.2.3 -> 2.0.0
         python scripts/version_sync.py 2.5.0      -> set explicit version
  3. Write the resulting version into EVERY file that needs to agree:
         • VERSION
         • pyproject.toml          ([project] version = "...")
         • app/src/core/config.py  (APP_VERSION = "...")

The final line printed to stdout is always the resulting version string
(e.g. "1.2.4") with nothing else on that line — scripts/release.py relies
on this to capture the new version programmatically.

Usage (via taskipy, mirrors npm-style scripts):
    task version:sync     -> sync only (no bump)
    task version:patch    -> bump patch + sync everywhere
    task version:minor    -> bump minor + sync everywhere
    task version:major     -> bump major + sync everywhere
────────────────────────────────────────────────────────────────────────────
"""

import re
import sys
from pathlib import Path

ROOT          = Path(__file__).resolve().parent.parent
VERSION_FILE  = ROOT / "VERSION"
PYPROJECT     = ROOT / "pyproject.toml"
CONFIG_PY     = ROOT / "app" / "src" / "core" / "config.py"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


# ── read ──────────────────────────────────────────────────────────────────

def read_current_version() -> str:
    if VERSION_FILE.exists():
        v = VERSION_FILE.read_text(encoding="utf-8").strip()
        if SEMVER_RE.match(v):
            return v

    # Fallback: try to recover a version from pyproject.toml
    if PYPROJECT.exists():
        m = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', PYPROJECT.read_text(encoding="utf-8"))
        if m:
            return m.group(1)

    return "0.1.0"


def bump_version(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump type: {part}")
    return f"{major}.{minor}.{patch}"


# ── write targets ────────────────────────────────────────────────────────

def write_version_file(version: str):
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")


def sync_pyproject(version: str):
    if not PYPROJECT.exists():
        return
    content = PYPROJECT.read_text(encoding="utf-8")

    if re.search(r'^\s*version\s*=\s*"[^"]*"', content, flags=re.MULTILINE):
        new_content = re.sub(
            r'^(\s*version\s*=\s*)"[^"]*"',
            rf'\1"{version}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        # No version key found at all — append one under [project]
        if "[project]" in content:
            new_content = content.replace(
                "[project]", f'[project]\nversion = "{version}"', 1
            )
        else:
            new_content = content + f'\n[project]\nversion = "{version}"\n'

    PYPROJECT.write_text(new_content, encoding="utf-8")


def sync_config_py(version: str):
    if not CONFIG_PY.exists():
        return
    content = CONFIG_PY.read_text(encoding="utf-8")

    if re.search(r'^APP_VERSION\s*=\s*"[^"]*"', content, flags=re.MULTILINE):
        new_content = re.sub(
            r'^APP_VERSION\s*=\s*"[^"]*"',
            f'APP_VERSION = "{version}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        new_content = content.rstrip() + (
            "\n\n# ── App Version ───────────────────────────────────────────\n"
            "# NOTE: auto-managed by scripts/version_sync.py\n"
            f'APP_VERSION = "{version}"\n'
        )

    CONFIG_PY.write_text(new_content, encoding="utf-8")


# ── main ──────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    current = read_current_version()

    if not args:
        target = current
        action = "synced"
    elif args[0] in ("major", "minor", "patch"):
        target = bump_version(current, args[0])
        action = f"bumped ({args[0]})"
    elif SEMVER_RE.match(args[0]):
        target = args[0]
        action = "set explicitly"
    else:
        print(f"ERROR: invalid argument '{args[0]}'. "
              f"Expected one of: major | minor | patch | X.Y.Z", file=sys.stderr)
        sys.exit(1)

    write_version_file(target)
    sync_pyproject(target)
    sync_config_py(target)

    if target != current:
        print(f"Version {action}: {current} -> {target}", file=sys.stderr)
    else:
        print(f"Version already in sync: {target}", file=sys.stderr)

    # IMPORTANT: this must be the last line on stdout, and contain
    # nothing but the version string — release.py parses it.
    print(target)


if __name__ == "__main__":
    main()