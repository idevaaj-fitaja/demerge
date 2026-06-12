#!/usr/bin/env python3
"""
Build a Windows-compatible Python venv from macOS (cross-platform build).

Downloads the Windows embeddable Python runtime and uses pip's cross-platform
install feature (`--platform win_amd64`) to install all dependencies.

Usage: python scripts/build_win_venv.py
Output: ./venv-win/
"""

import os
import sys
import shutil
import re
import zipfile
import urllib.request
import subprocess
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VENV_WIN_DIR = ROOT_DIR / "venv-win"
PYTHON_VERSION = "3.14.5"
PYTHON_SHORT = "".join(PYTHON_VERSION.rsplit(".", 1)[0])
PYTHON_ZIP_NAME = re.sub(r"\.", "", PYTHON_VERSION.rsplit(".", 1)[0])  # → "314"
PYTHON_ZIP_GLOB = f"python{PYTHON_ZIP_NAME}.zip"  # → python314.zip

EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)

# For Windows build, avoid uvloop (Unix-only). Use standard uvicorn extras
# that are available on Windows.
WIN_REQUIREMENTS = [
    "fastapi",
    "uvicorn",
    "httptools",
    "watchfiles",
    "websockets",
    "python-multipart",
    "pypdf2",
    "pyhanko",
    "pydantic",
    "python-dotenv",
]


def download_file(url: str, dest: Path):
    print(f"  Downloading...", end=" ", flush=True)
    urllib.request.urlretrieve(url, dest)
    print(f"done ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def clean_venv():
    if VENV_WIN_DIR.exists():
        print(f"Removing existing {VENV_WIN_DIR}...")
        shutil.rmtree(VENV_WIN_DIR)


def step(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def setup_venv_structure():
    ensure_dir(VENV_WIN_DIR / "Scripts")
    ensure_dir(VENV_WIN_DIR / "Lib" / "site-packages")
    print("  Directory structure created")


def download_and_copy_python_runtime(tmp_dir: Path):
    embed_zip = tmp_dir / "embed.zip"
    extract_dir = tmp_dir / "embed"

    download_file(EMBED_URL, embed_zip)

    print("  Extracting...", end=" ", flush=True)
    with zipfile.ZipFile(embed_zip, "r") as zf:
        zf.extractall(extract_dir)
    print("done")

    # Patch ._pth to allow site-packages
    pth_files = list(extract_dir.glob("python*._pth"))
    if pth_files:
        pth = pth_files[0]
        content = pth.read_text()
        # Ensure Lib/site-packages is in the path
        if "Lib/site-packages" not in content:
            content = content.replace(
                PYTHON_ZIP_GLOB,
                f"{PYTHON_ZIP_GLOB}\nLib/site-packages"
            )
        # Uncomment import site
        content = content.replace("#import site", "import site")
        pth.write_text(content)
        print(f"  Patched {pth.name}")

    # Copy runtime files to Scripts/
    for ext in ("*.exe", "*.dll", "*.pyd"):
        for f in extract_dir.glob(ext):
            if f.is_file():
                shutil.copy2(f, VENV_WIN_DIR / "Scripts" / f.name)

    for f in extract_dir.glob("python*._pth"):
        shutil.copy2(f, VENV_WIN_DIR / "Scripts" / f.name)

    for f in extract_dir.glob(PYTHON_ZIP_GLOB):
        shutil.copy2(f, VENV_WIN_DIR / "Scripts" / f.name)

    # Copy all remaining files (stdlib modules, etc.)
    for item in extract_dir.iterdir():
        if item.is_file() and not any(
            p in str(item) for p in [".exe", ".dll", ".pyd", "._pth", ".zip"]
        ):
            shutil.copy2(item, VENV_WIN_DIR / "Scripts" / item.name)

    # Copy Lib/ directory (stdlib)
    src_lib = extract_dir / "Lib"
    if src_lib.exists():
        for item in src_lib.iterdir():
            dest = VENV_WIN_DIR / "Lib" / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    print("  Python runtime copied")


def install_wheels_cross(host_python: str):
    site_packages = VENV_WIN_DIR / "Lib" / "site-packages"

    print("  Installing packages for win_amd64...")

    # First install with --only-binary for native packages
    result = subprocess.run(
        [host_python, "-m", "pip", "install",
         "--platform", "win_amd64",
         "--python-version", "3.14",
         "--target", str(site_packages),
         "--only-binary=:all:",
         "--no-warn-script-location",
         *WIN_REQUIREMENTS],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"  Binary install issues (expected for some packages):")
        for line in result.stderr.splitlines()[-10:]:
            print(f"    {line}")

        # Retry remaining packages without --only-binary
        print("  Retrying with source builds allowed...")
        result = subprocess.run(
            [host_python, "-m", "pip", "install",
             "--platform", "win_amd64",
             "--python-version", "3.14",
             "--target", str(site_packages),
             "--no-warn-script-location",
             *WIN_REQUIREMENTS],
            capture_output=True, text=True
        )

    # Print what was installed
    for line in result.stdout.splitlines():
        if "Installed" in line or "installed" in line or "Requirement" in line:
            print(f"    {line}")
    if result.returncode != 0:
        for line in result.stderr.splitlines()[-5:]:
            print(f"    {line}")

    # Explicitly install pyhanko dependencies in case they were missed
    print("  Ensuring pyhanko native deps...")
    for extra_pkg in ["lxml", "cryptography", "cffi", "pyhanko-certvalidator"]:
        subprocess.run(
            [host_python, "-m", "pip", "install",
             "--platform", "win_amd64",
             "--python-version", "3.14",
             "--target", str(site_packages),
             "--only-binary=:all:",
             "--no-warn-script-location",
             extra_pkg],
            capture_output=True, text=True
        )

    # Remove pip itself from site-packages (not needed at runtime)
    for d in (site_packages / "pip", site_packages / "pip-26.1.1.dist-info"):
        if d.exists():
            shutil.rmtree(d)

    print("  Dependencies installed")


def create_pyvenv_cfg():
    # Use generic home path that works on any Windows machine
    content = f"""home = C:\\Python{PYTHON_SHORT}
include-system-site-packages = false
version = {PYTHON_VERSION}
"""
    (VENV_WIN_DIR / "pyvenv.cfg").write_text(content)
    print("  Created pyvenv.cfg")


def verify_structure():
    print("\n--- Verification ---")
    checks = [
        ("Scripts/python.exe", VENV_WIN_DIR / "Scripts" / "python.exe"),
        ("Scripts/python3.dll", VENV_WIN_DIR / "Scripts" / "python3.dll"),
        (f"Scripts/python{PYTHON_SHORT}.dll",
         VENV_WIN_DIR / "Scripts" / f"python{PYTHON_SHORT}.dll"),
        ("Lib/site-packages", VENV_WIN_DIR / "Lib" / "site-packages"),
        ("pyvenv.cfg", VENV_WIN_DIR / "pyvenv.cfg"),
    ]

    for label, path in checks:
        status = "✓" if path.exists() else "✗ MISSING"
        print(f"  [{status}] {label}")

    # Check for essential packages
    essential = ["fastapi", "pydantic", "uvicorn", "pypdf2"]
    site_pkgs = VENV_WIN_DIR / "Lib" / "site-packages"
    for pkg in essential:
        pkg_dir = site_pkgs / pkg
        status = "✓" if pkg_dir.exists() else "✗ MISSING"
        print(f"  [{status}] site-packages/{pkg}")

    total_size = sum(
        f.stat().st_size for f in VENV_WIN_DIR.rglob("*") if f.is_file()
    )
    print(f"\n  Total size: {total_size / 1024 / 1024:.1f} MB")


def main():
    print("=== Building Windows Python venv for Demerge ===\n")

    clean_venv()

    with tempfile.TemporaryDirectory(prefix="win_venv_") as tmp:
        tmp_dir = Path(tmp)

        step("Setting up directory structure")
        setup_venv_structure()

        step("Downloading Windows Python runtime")
        download_and_copy_python_runtime(tmp_dir)

        step("Installing Windows wheels (cross-platform)")
        install_wheels_cross(sys.executable)

    step("Finalizing venv")
    create_pyvenv_cfg()
    verify_structure()

    print(f"\n=== Done ===")
    print(f"Windows venv: {VENV_WIN_DIR}")
    print(f"Build Windows app: cd electron && npm run build:win")

    # Also print instructions for swapping venv
    print()
    print("NOTE: Before building for Windows, temporarily rename venv-minimal")
    print(f"      and replace it with {VENV_WIN_DIR}:")


if __name__ == "__main__":
    main()
