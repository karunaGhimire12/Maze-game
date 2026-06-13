from pathlib import Path
import subprocess
import shutil

# Clean old builds
for folder in ["build", "dist"]:
    if Path(folder).exists():
        shutil.rmtree(folder)

# Build exe
subprocess.run([
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--name",
    "MazeGame",
     "--paths=app/src",
    "app/src/main.py"
], check=True)

print("Build completed.")
print("Executable: dist/MazeGame.exe")