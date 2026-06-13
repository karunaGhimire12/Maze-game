import sys
import re
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: task version <version>")
    exit(1)

new_version = sys.argv[1]

pyproject = Path("pyproject.toml")

content = pyproject.read_text(encoding="utf-8")

content = re.sub(
    r'version\s*=\s*"[^"]+"',
    f'version = "{new_version}"',
    content
)

pyproject.write_text(content, encoding="utf-8")

print(f"Version updated -> {new_version}")