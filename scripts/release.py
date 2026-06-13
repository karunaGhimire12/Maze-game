"""
scripts/release.py
────────────────────────────────────────────────────────────────────────────
One-command, fully automated release pipeline — the Python equivalent of:

    "release:start": "node ./scripts/start-release.mjs"

Running:

    task release            (defaults to a PATCH bump)
    task release:patch
    task release:minor
    task release:major

does ALL of the following, with zero manual steps:

    1. Bump + sync the version everywhere      (scripts/version_sync.py)
    2. Build the standalone executable          (scripts/build.py)
    3. Commit the version bump                  (git commit)
    4. Create an annotated git tag "vX.Y.Z"     (git tag)
    5. Push the commit + tag to GitHub          (git push)
    6. Create a GitHub Release with a generated
       title/tagline, auto-generated notes, and
       the built executable attached            (gh release create)

Requirements (checked up front, with friendly errors if missing):
    • git                — https://git-scm.com
    • gh (GitHub CLI)    — https://cli.github.com   (run `gh auth login` once)
    • pyinstaller        — pip install pyinstaller

Safety:
    • Aborts early if the target tag already exists.
    • Aborts if there are uncommitted changes OTHER than the version files
      (so you never accidentally ship unrelated work-in-progress).
    • Skips the "commit version bump" step gracefully if the version did
      not actually change (e.g. re-running after a manual sync).
────────────────────────────────────────────────────────────────────────────
"""

from pathlib import Path
import subprocess
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent

# Files that are allowed (and expected) to change as part of a version bump.
VERSION_FILES = ["VERSION", "pyproject.toml", "app/src/core/config.py"]

APP_NAME    = "MazeQuest"
DISPLAY_NAME = "Maze Quest"


# ── helpers ─────────────────────────────────────────────────────────────

def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, cwd=ROOT, **kw)


def run_out(cmd) -> str:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.stdout.strip()


def require_tool(name: str, hint: str):
    if shutil.which(name) is None:
        print(f"ERROR: required tool '{name}' was not found on PATH.\n  -> {hint}",
              file=sys.stderr)
        sys.exit(1)


def step(n: int, total: int, label: str):
    print(f"\n[{n}/{total}] {label}")


# ── main pipeline ──────────────────────────────────────────────────────────

def main():
    bump = sys.argv[1] if len(sys.argv) > 1 else "patch"
    if bump not in ("major", "minor", "patch"):
        print("Usage: task release [major|minor|patch]   (default: patch)",
              file=sys.stderr)
        sys.exit(1)

    TOTAL = 6

    # ── Pre-flight checks ───────────────────────────────────────────────
    require_tool("git", "Install from https://git-scm.com and ensure it's on PATH.")
    require_tool("gh",  "Install the GitHub CLI from https://cli.github.com, "
                          "then run `gh auth login` once.")
    require_tool("pyinstaller", "Install with: pip install pyinstaller")

    # Ensure we're inside a git repo
    try:
        run_out(["git", "rev-parse", "--is-inside-work-tree"])
    except subprocess.CalledProcessError:
        print("ERROR: not inside a git repository.", file=sys.stderr)
        sys.exit(1)

    # Reject dirty working tree (other than the version-sync files we expect
    # to modify ourselves in step 1).
    status_lines = [l for l in run_out(["git", "status", "--porcelain"]).splitlines() if l]
    unexpected = [
        l for l in status_lines
        if not any(l.endswith(vf) or vf in l for vf in VERSION_FILES)
    ]
    if unexpected:
        print("ERROR: working tree has uncommitted changes unrelated to the "
              "version bump:\n  " + "\n  ".join(unexpected) +
              "\nCommit or stash these first, then re-run `task release`.",
              file=sys.stderr)
        sys.exit(1)

    # ── 1. Bump + sync version ──────────────────────────────────────────
    step(1, TOTAL, f"Bumping version ({bump}) and syncing across the project...")
    new_version = run_out([sys.executable, "scripts/version_sync.py", bump]).splitlines()[-1].strip()
    tag = f"v{new_version}"
    print(f"  -> {tag}")

    existing_tags = run_out(["git", "tag"]).splitlines()
    if tag in existing_tags:
        print(f"ERROR: tag {tag} already exists. Bump again or delete the "
              f"existing tag (`git tag -d {tag}` locally and on GitHub) "
              f"before retrying.", file=sys.stderr)
        sys.exit(1)

    # ── 2. Build executable ─────────────────────────────────────────────
    step(2, TOTAL, "Building standalone executable...")
    run([sys.executable, "scripts/build.py"])

    exe_win = ROOT / "dist" / f"{APP_NAME}.exe"
    exe_nix = ROOT / "dist" / APP_NAME
    exe = exe_win if exe_win.exists() else exe_nix
    if not exe.exists():
        print("ERROR: build did not produce an executable in dist/.", file=sys.stderr)
        sys.exit(1)
    print(f"  -> {exe.relative_to(ROOT)}")

    # ── 3. Commit version bump ───────────────────────────────────────────
    step(3, TOTAL, "Committing version bump...")
    run(["git", "add", *VERSION_FILES])
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff_check.returncode != 0:
        run(["git", "commit", "-m", f"chore(release): {tag}"])
    else:
        print("  -> No version changes to commit (already in sync).")

    # ── 4. Create annotated tag ──────────────────────────────────────────
    step(4, TOTAL, f"Creating annotated tag {tag}...")
    tagline = f"{DISPLAY_NAME} {tag}"
    run(["git", "tag", "-a", tag, "-m", tagline])

    # ── 5. Push commit + tag ─────────────────────────────────────────────
    step(5, TOTAL, "Pushing commit and tag to GitHub...")
    run(["git", "push"])
    run(["git", "push", "origin", tag])

    # ── 6. Publish GitHub release with binary attached ──────────────────
    step(6, TOTAL, "Publishing GitHub release...")
    release_title = f"{DISPLAY_NAME} {tag}"
    run([
        "gh", "release", "create", tag,
        str(exe),
        "--title", release_title,
        "--generate-notes",
    ])

    print(f"\n✅ Release {tag} published successfully!")
    print(f"   Title:      {release_title}")
    print(f"   Executable: {exe.name}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)