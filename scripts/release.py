"""
scripts/release.py
────────────────────────────────────────────────────────────────────────────
One-command, fully automated release pipeline — the Python equivalent of:

    "release:start": "node ./scripts/start-release.mjs"

Running:

    task release            (releases the CURRENT version — no bump)
    task release:patch      (bumps patch, then releases)
    task release:minor      (bumps minor, then releases)
    task release:major      (bumps major, then releases)

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
    • Aborts early if the target tag already exists (unless it's a RESUME —
      see below).
    • Aborts if there are uncommitted changes OTHER than the version files
      (so you never accidentally ship unrelated work-in-progress).
    • Skips the "commit version bump" step gracefully if the version did
      not actually change (e.g. re-running after a manual sync).

────────────────────────────────────────────────────────────────────────────
RESUMABLE RELEASES
────────────────────────────────────────────────────────────────────────────
If `task release` is interrupted AFTER the local commit + tag were created
but BEFORE the push/publish succeeded (e.g. your network drops, GitHub is
briefly unreachable, `gh auth` expired, etc.), simply run `task release`
again with NO changes in between.

The script detects that HEAD is already tagged with a version matching the
current VERSION file, and treats this as an UNFINISHED release: it skips
straight to push + publish instead of bumping the version again. This means
you never end up with orphaned "vX.Y.Z" tags from failed runs — just fix
whatever went wrong (check your connection, re-run `gh auth login`, etc.)
and run `task release` again.
────────────────────────────────────────────────────────────────────────────
"""

from pathlib import Path
import subprocess
import shutil
import sys
import re

ROOT = Path(__file__).resolve().parent.parent

# Files that are allowed (and expected) to change as part of a version bump.
VERSION_FILES = ["VERSION", "pyproject.toml", "app/src/core/config.py"]

APP_NAME     = "MazeQuest"
DISPLAY_NAME = "Maze Quest"

TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")


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


def try_run_out(cmd):
    """Like run_out, but returns (ok, output) instead of raising."""
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (result.returncode == 0, result.stdout.strip(), result.stderr.strip())


def require_tool(name: str, hint: str):
    if shutil.which(name) is None:
        print(f"ERROR: required tool '{name}' was not found on PATH.\n  -> {hint}",
              file=sys.stderr)
        sys.exit(1)


def step(n: int, total: int, label: str):
    print(f"\n[{n}/{total}] {label}")


def read_version_file() -> str:
    vf = ROOT / "VERSION"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    return ""


def head_tag() -> str | None:
    """If HEAD is exactly tagged with something matching vX.Y.Z, return it."""
    ok, out, _ = try_run_out(["git", "describe", "--tags", "--exact-match", "HEAD"])
    if ok and TAG_RE.match(out):
        return out
    return None


def find_exe() -> Path | None:
    exe_win = ROOT / "dist" / f"{APP_NAME}.exe"
    exe_nix = ROOT / "dist" / APP_NAME
    if exe_win.exists():
        return exe_win
    if exe_nix.exists():
        return exe_nix
    return None


def github_release_exists(tag: str) -> bool:
    ok, _, _ = try_run_out(["gh", "release", "view", tag])
    return ok


# ── main pipeline ──────────────────────────────────────────────────────────

def main():
    # Default: NO version bump — release whatever version is currently in
    # the VERSION file (after a no-op sync to keep all files consistent).
    # Pass "major" / "minor" / "patch" explicitly to bump first.
    bump = sys.argv[1] if len(sys.argv) > 1 else "none"
    if bump not in ("major", "minor", "patch", "none"):
        print("Usage: task release [major|minor|patch]\n"
              "       (no argument = release current version, no bump)",
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

    # ── RESUME DETECTION ─────────────────────────────────────────────────
    # If HEAD is already tagged "vX.Y.Z" matching the current VERSION file,
    # a previous `task release` got as far as commit+tag but failed before
    # push/publish. Resume from step 5 instead of bumping again.
    current_version = read_version_file()
    existing_head_tag = head_tag()
    resuming = (
        existing_head_tag is not None
        and current_version != ""
        and existing_head_tag == f"v{current_version}"
    )

    # Reject dirty working tree (other than the version-sync files we expect
    # to modify ourselves in step 1) — but only when NOT resuming, since a
    # resume should already have a clean tree from the prior commit.
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

    if resuming:
        tag = existing_head_tag
        new_version = current_version
        print(f"\n⏯  Detected unfinished release for {tag} "
              f"(local commit + tag already exist).")
        print(f"   Resuming from step 5/{TOTAL} — push + publish only.\n")

        exe = find_exe()
        if exe is None:
            print("  (dist/ executable missing — rebuilding...)")
            run([sys.executable, "scripts/build.py"])
            exe = find_exe()
            if exe is None:
                print("ERROR: build did not produce an executable in dist/.", file=sys.stderr)
                sys.exit(1)
        print(f"  -> using existing build: {exe.relative_to(ROOT)}")

    else:
        # ── 1. Sync version (and bump it first, if requested) ────────────
        if bump == "none":
            step(1, TOTAL, "Syncing current version across the project (no bump)...")
            sync_args = []
        else:
            step(1, TOTAL, f"Bumping version ({bump}) and syncing across the project...")
            sync_args = [bump]

        new_version = run_out([sys.executable, "scripts/version_sync.py", *sync_args]).splitlines()[-1].strip()
        tag = f"v{new_version}"
        print(f"  -> {tag}")

        existing_tags = run_out(["git", "tag"]).splitlines()
        if tag in existing_tags:
            if bump == "none":
                print(f"ERROR: tag {tag} already exists — this version has "
                      f"already been released.\n"
                      f"  -> Bump the version first: "
                      f"`task release:patch` / `:minor` / `:major`\n"
                      f"  -> Or, if you just want to publish a new build for "
                      f"the SAME version, delete the old tag first:\n"
                      f"       git tag -d {tag}\n"
                      f"       git push --delete origin {tag}\n"
                      f"       gh release delete {tag}", file=sys.stderr)
            else:
                print(f"ERROR: tag {tag} already exists. Bump again or delete the "
                      f"existing tag (`git tag -d {tag}` locally and on GitHub) "
                      f"before retrying.", file=sys.stderr)
            sys.exit(1)

        # ── 2. Build executable ─────────────────────────────────────────
        step(2, TOTAL, "Building standalone executable...")
        run([sys.executable, "scripts/build.py"])

        exe = find_exe()
        if exe is None:
            print("ERROR: build did not produce an executable in dist/.", file=sys.stderr)
            sys.exit(1)
        print(f"  -> {exe.relative_to(ROOT)}")

        # ── 3. Commit version bump ───────────────────────────────────────
        step(3, TOTAL, "Committing version bump...")
        run(["git", "add", *VERSION_FILES])
        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if diff_check.returncode != 0:
            run(["git", "commit", "-m", f"chore(release): {tag}"])
        else:
            print("  -> No version changes to commit (already in sync).")

        # ── 4. Create annotated tag ──────────────────────────────────────
        step(4, TOTAL, f"Creating annotated tag {tag}...")
        tagline = f"{DISPLAY_NAME} {tag}"
        run(["git", "tag", "-a", tag, "-m", tagline])

    # ── 5. Push commit + tag ─────────────────────────────────────────────
    step(5, TOTAL, "Pushing commit and tag to GitHub...")
    try:
        run(["git", "push"])
        run(["git", "push", "origin", tag])
    except subprocess.CalledProcessError:
        print(f"\n⚠  Push failed (network/auth issue?). Your commit and tag "
              f"{tag} are safe locally.\n"
              f"   Fix the connection / auth issue, then just run "
              f"`task release` again — it will resume from this exact step.",
              file=sys.stderr)
        sys.exit(1)

    # ── 6. Publish GitHub release with binary attached ──────────────────
    step(6, TOTAL, "Publishing GitHub release...")
    release_title = f"{DISPLAY_NAME} {tag}"
    try:
        if github_release_exists(tag):
            print(f"  -> Release {tag} already exists on GitHub; "
                  f"uploading/refreshing the executable asset.")
            run(["gh", "release", "upload", tag, str(exe), "--clobber"])
        else:
            run([
                "gh", "release", "create", tag,
                str(exe),
                "--title", release_title,
                "--generate-notes",
            ])
    except subprocess.CalledProcessError:
        print(f"\n⚠  GitHub release step failed (network/auth issue?). "
              f"Your commit, tag, and push are already complete.\n"
              f"   Fix the issue, then just run `task release` again — it "
              f"will resume from this exact step.",
              file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ Release {tag} published successfully!")
    print(f"   Title:      {release_title}")
    print(f"   Executable: {exe.name}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)