"""
scripts/build.py
────────────────────────────────────────────────────────────────────────────
Builds a standalone executable of Maze Quest with PyInstaller.

    task build

Output:
    dist/MazeQuest(.exe)
────────────────────────────────────────────────────────────────────────────
"""

from pathlib import Path
import subprocess
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "MazeQuest"


def main():
    # Clean old build artifacts
    for folder in ("build", "dist"):
        p = ROOT / folder
        if p.exists():
            shutil.rmtree(p)

    spec = ROOT / f"{APP_NAME}.spec"
    if spec.exists():
        spec.unlink()

    print(f"Building {APP_NAME}...")
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", APP_NAME,
            "--paths=app/src",
            "app/src/main.py",
        ],
        check=True,
        cwd=ROOT,
    )

    exe_win = ROOT / "dist" / f"{APP_NAME}.exe"
    exe_nix = ROOT / "dist" / APP_NAME
    exe = exe_win if exe_win.exists() else exe_nix

    if not exe.exists():
        print("ERROR: build did not produce an output binary in dist/", file=sys.stderr)
        sys.exit(1)

    print("Build completed.")
    print(f"Executable: {exe.relative_to(ROOT)}")


if __name__ == "__main__":
    main()