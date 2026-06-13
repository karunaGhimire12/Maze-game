from pathlib import Path
import subprocess
import re
import sys

# Read version
content = Path("pyproject.toml").read_text()

match = re.search(
    r'version\s*=\s*"([^"]+)"',
    content
)

if not match:
    raise Exception("Version not found")

version = match.group(1)
tag = f"v{version}"

print(f"Building {tag}")

# Build executable
subprocess.run([
    "pyinstaller",
    "--onefile",
    "--windowed",
    "app/src/main.py"
], check=True)

exe = Path("dist/main.exe")

if not exe.exists():
    raise Exception("Build failed")

existing_tags = subprocess.check_output(
    ["git", "tag"],
    text=True
).splitlines()

if tag in existing_tags:
    raise Exception(
        f"{tag} already exists. Run:\n"
        f"task version <new_version>"
    )

# Git operations
commands = [
    ["git", "add", "."],
    ["git", "commit", "-m", f"release: {tag}"],
    ["git", "tag", tag],
    ["git", "push"],
    ["git", "push", "origin", tag]
]

for cmd in commands:
    subprocess.run(cmd, check=True)

# Create release and upload exe
subprocess.run([
    "gh",
    "release",
    "create",
    tag,
    str(exe),
    "--title",
    tag,
    "--generate-notes"
], check=True)

print(f"Release {tag} published")