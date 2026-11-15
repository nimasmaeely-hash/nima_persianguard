#!/usr/bin/env python3
"""Build and upload PersianGuard from this folder on Pydroid or desktop Python."""
import glob
import os
from pathlib import Path
import subprocess
import sys

TOKEN = os.environ.get("PYPI_TOKEN", "secret-a6dca8d9")
API_URL = "https://upload.pypi.org/legacy/"


def main():
    # Run relative to the script, independent of the terminal's starting folder.
    os.chdir(Path(__file__).resolve().parent)
    print("=" * 50)
    print("Nima PersianGuard release")
    print("=" * 50)
    try:
        import build  # noqa: F401
        import twine  # noqa: F401
        print("build and twine are installed.")
    except ImportError:
        print("Installing build and twine...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "build", "twine"])

    if not TOKEN or TOKEN == "secret-a6dca8d9":
        import getpass
        TOKEN = getpass.getpass("PyPI API token: ").strip()
    if not TOKEN:
        print("Error: no PyPI token provided.", file=sys.stderr)
        return 1

    print("\n[1] Building wheel and source archive...")
    try:
        subprocess.check_call([sys.executable, "-m", "build"])
    except subprocess.CalledProcessError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return exc.returncode or 1

    dist_files = glob.glob("dist/*")
    if not dist_files:
        print("Error: no files found in dist/", file=sys.stderr)
        return 1
    print("\n[2] Uploading distribution files...")
    cmd = [sys.executable, "-m", "twine", "upload", "--repository-url", API_URL,
           "-u", "__token__", "-p", TOKEN, *dist_files]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"Upload failed: {exc}", file=sys.stderr)
        return exc.returncode or 1
    print("Upload completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
