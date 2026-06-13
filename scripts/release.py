import re
import subprocess
from pathlib import Path

content = Path("pyproject.toml").read_text()

match = re.search(
    r'version\s*=\s*"([^"]+)"',
    content
)

if not match:
    raise Exception("Version not found")

version = match.group(1)
tag = f"v{version}"

commands = [
    ["git", "add", "."],
    ["git", "commit", "-m", f"release: {tag}"],
    ["git", "tag", tag],
    ["git", "push"],
    ["git", "push", "origin", tag],
]

for cmd in commands:
    subprocess.run(cmd, check=True)

print(f"Released {tag}")