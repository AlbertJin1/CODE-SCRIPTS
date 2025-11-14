# build_exe.py
import os
import subprocess
import shutil


def build():
    print("Building CompressMaster.exe...")

    # Clean old builds
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    if os.path.exists("CompressMaster.spec"):
        os.remove("CompressMaster.spec")

    # PyInstaller command (NO ICON, NO UPX)
    cmd = [
        "pyinstaller",
        "--name=CompressMaster",
        "--windowed",
        "--onedir",
        "--clean",
        "--noconfirm",
        "main.py",
    ]

    subprocess.run(cmd, check=True)
    print("Build complete: dist/CompressMaster/")


if __name__ == "__main__":
    build()
