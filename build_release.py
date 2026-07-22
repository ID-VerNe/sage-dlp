"""
SageDLP Release Build Script
=============================
Builds a standalone Windows executable using PyInstaller,
packages browser extension, and prepares the release artifacts.

Usage:
    python build_release.py        # Production build
    python build_release.py --dev  # Dev build (faster, no UPX, debug)
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
PYTHON_EXE = ROOT / "python_embed" / "python.exe"
PYINSTALLER = ROOT / "python_embed" / "Scripts" / "pyinstaller.exe"

# ── Version ───────────────────────────────────────────────────────────────
VERSION = "5.2.0"


# ── Paths ─────────────────────────────────────────────────────────────────
def get_dirs(dev: bool) -> dict:
    suffix = "-dev" if dev else ""
    build_dir = ROOT / "build"
    return {
        "dist": build_dir / f"dist{suffix}",       # PyInstaller intermediate output
        "build": build_dir / f"work{suffix}",       # PyInstaller work directory
        "spec": ROOT / f"SageDLP{suffix}.spec",    # spec file (at root, PyInstaller constraint)
        "output": build_dir,                        # Final output directory
        "exe_name": "SageDLP.exe",
        "app_dir": build_dir / f"dist{suffix}" / "SageDLP",
    }


# ── Clean ─────────────────────────────────────────────────────────────────
def clean_build(dev: bool):
    dirs = get_dirs(dev)
    # Clean the intermediate build directories
    for d in [dirs["build"], dirs["dist"]]:
        if d.exists():
            print(f"  Cleaning: {d}")
            shutil.rmtree(d, ignore_errors=True)
    # Also clean spec file
    if dirs["spec"].exists():
        os.remove(dirs["spec"])


# ── PyInstaller ───────────────────────────────────────────────────────────
def build_exe(dev: bool, dirs: dict) -> bool:
    """
    Build SageDLP.exe with PyInstaller.
    Returns True on success.
    """
    if not PYINSTALLER.exists():
        print(f"[ERROR] PyInstaller not found at {PYINSTALLER}")
        print("  Run: python_embed/Scripts/pip.exe install PyInstaller")
        return False

    # Gather data files
    datas = [
        (str(ROOT / "sage_dlp" / "assets"), "sage_dlp/assets"),
        (str(ROOT / "sage_dlp" / "languages"), "sage_dlp/languages"),
    ]

    # Hidden imports – only what the app actually uses
    hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtNetwork",
        "PySide6.QtSvg",
        # Additional dependencies
        "packaging",
        "markdown",
        "loguru",
        "requests",
        "PIL",
        "PIL._imaging",
    ]

    # PySide6 modules that add huge bloat but are NOT used by the app
    # (QtWebEngine alone is 196MB, Qt3D ~50MB, QML/QtQuick ~60MB, etc.)
    unused_modules = [
        "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
        "PySide6.QtBluetooth", "PySide6.QtCharts", "PySide6.QtConcurrent",
        "PySide6.QtDataVisualization", "PySide6.QtDBus", "PySide6.QtDesigner",
        "PySide6.QtGraphs", "PySide6.QtGraphsWidgets",
        "PySide6.QtHelp", "PySide6.QtHttpServer",
        "PySide6.QtLocation", "PySide6.QtNfc",
        "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtPositioning", "PySide6.QtPrintSupport",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
        "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects",
        "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialBus",
        "PySide6.QtSerialPort", "PySide6.QtSpatialAudio",
        "PySide6.QtSql", "PySide6.QtStateMachine",
        "PySide6.QtTest", "PySide6.QtTextToSpeech",
        "PySide6.QtUiTools", "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets",
        "PySide6.QtXml",
    ]

    # Build command – use Python module to invoke PyInstaller
    cmd = [
        str(PYTHON_EXE),
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "SageDLP",
        "--distpath", str(dirs["dist"]),
        "--workpath", str(dirs["build"]),
        "--specpath", str(ROOT),
        # Single-file EXE (everything bundled inside)
        "--onefile",
        # Windowed (no console) for production
        "--windowed",
        # Icon
        "--icon", str(ROOT / "sage_dlp" / "assets" / "Icon" / "icon.png"),
        # Module path
        "--paths", str(ROOT),
        # Debug level
        "--log-level", "WARN" if not dev else "DEBUG",
    ]

    # Add data files (assets, languages, browser_ext — all bundled into the EXE)
    for src, dst in datas:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
    # Also bundle browser_ext for distribution
    browser_ext_src = ROOT / "sage_dlp" / "browser_ext"
    if browser_ext_src.exists():
        cmd.extend(["--add-data", f"{str(browser_ext_src)}{os.pathsep}browser_ext"])

    # Add hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Exclude unused PySide6 modules to save ~400MB+
    for mod in unused_modules:
        cmd.extend(["--exclude-module", mod])

    # Collect only the small deps (not PySide6 — it's handled by hidden imports + hook)
    cmd.extend([
        "--collect-all", "loguru",
        "--collect-all", "packaging",
        "--collect-all", "PIL",
    ])

    # Entry point
    cmd.append(str(ROOT / "sage_dlp" / "main.py"))

    print(f"\n{'='*60}")
    print(f"  Building SageDLP v{VERSION} {'(DEV)' if dev else '(PRODUCTION)'}")
    print(f"  PyInstaller: {PYINSTALLER}")
    print(f"  Output: {dirs['dist']}")
    print(f"{'='*60}\n")

    start = time.time()
    result = subprocess.run(cmd, cwd=str(ROOT))
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n[ERROR] PyInstaller build failed (exit code {result.returncode})")
        return False

    print(f"\n  PyInstaller completed in {elapsed:.1f}s")
    return True


# ── Post-build: assemble release ─────────────────────────────────────────
def assemble_release(dev: bool, dirs: dict):
    """Verify the single-file EXE build and prepare artifacts."""
    # With --onefile, PyInstaller outputs a single SageDLP.exe directly
    pyi_output = dirs["dist"] / "SageDLP"
    exe_file = dirs["dist"] / "SageDLP.exe"
    if exe_file.exists():
        print(f"  Single-file EXE found: {exe_file}")
    elif pyi_output.exists() and (pyi_output / "SageDLP.exe").exists():
        # --onedir fallback
        exe_file = pyi_output / "SageDLP.exe"
    else:
        print(f"[ERROR] SageDLP.exe not found in {dirs['dist']}")
        return False

    # Move to final output directory
    final_dir = dirs["output"]
    if exe_file.parent == dirs["dist"]:
        # Single-file mode: exe is directly in dist/
        shutil.move(str(exe_file), str(final_dir / "SageDLP.exe"))
        # Clean up any leftover PyInstaller junk
        if pyi_output.exists():
            shutil.rmtree(pyi_output, ignore_errors=True)
    else:
        # One-dir mode: move the whole directory
        final_exe_dir = final_dir / "SageDLP"
        if final_exe_dir.exists():
            shutil.rmtree(final_exe_dir, ignore_errors=True)
        shutil.move(str(pyi_output), str(final_exe_dir))

    # Clean up the now-empty dist directory
    if dirs["dist"].exists():
        shutil.rmtree(dirs["dist"], ignore_errors=True)

    # Verify
    exe = final_dir / "SageDLP.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n  SageDLP.exe size: {size_mb:.1f} MB")
    else:
        # one-dir mode
        exe = final_dir / "SageDLP" / "SageDLP.exe"
        if exe.exists():
            size_mb = exe.stat().st_size / (1024 * 1024)
            print(f"\n  SageDLP.exe size: {size_mb:.1f} MB")

    return True


# ── Generate Inno Setup installer ────────────────────────────────────────
def generate_installer(dev: bool, dirs: dict):
    """Generate or suggest Inno Setup installer creation."""
    if dev:
        print("  [SKIP] Dev build: skipping installer generation")
        return

    iscc = shutil.which("iscc")
    iss_template = ROOT / "setup-scripts" / "Setup-windows.iss"

    if not iscc:
        print("  [INFO] Inno Setup (iscc.exe) not found on PATH.")
        print("  Creating portable zip instead...")
        return create_portable_zip(dirs)

    if not iss_template.exists():
        print(f"  [WARN] Setup script not found: {iss_template}")
        return create_portable_zip(dirs)

    print(f"  Running Inno Setup: {iss_template}")
    cmd = [
        iscc,
        f'/DMyAppVersion={VERSION}',
        f'/DSourceDir={dirs["output"] / "SageDLP"}',
        f'/DMyAppExeName=SageDLP.exe',
        str(iss_template),
    ]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        # Inno Setup outputs to OutputDir defined in .iss,
        # which is 'artifacts/' — move to build/
        inno_dir = ROOT / "artifacts"
        if inno_dir.exists():
            for f in inno_dir.iterdir():
                dest = dirs["output"] / f.name
                shutil.move(str(f), str(dest))
                sz = dest.stat().st_size / (1024 * 1024)
                print(f"  Installer: {dest.name}  ({sz:.1f} MB)")
            shutil.rmtree(inno_dir, ignore_errors=True)
    else:
        print(f"  [WARN] Inno Setup failed (exit code {result.returncode})")
        create_portable_zip(dirs)


def create_portable_zip(dirs: dict) -> bool:
    """Create a portable zip archive of the build."""
    import zipfile

    exe = dirs["output"] / "SageDLP.exe"
    if not exe.exists():
        print(f"  [ERROR] SageDLP.exe not found at {exe}")
        return False

    zip_name = dirs["output"] / f"SageDLP-v{VERSION}-Portable.zip"
    print(f"  Creating portable zip: {zip_name}")
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe, "SageDLP.exe")

    sz = zip_name.stat().st_size / (1024 * 1024)
    print(f"  Portable zip size: {sz:.1f} MB")
    return True


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SageDLP Release Builder")
    parser.add_argument("--dev", action="store_true", help="Dev build (debug, no installer)")
    args = parser.parse_args()

    dev = args.dev
    dirs = get_dirs(dev)

    print("╔══════════════════════════════════════════╗")
    print("║        SageDLP Release Builder           ║")
    print(f"║        Version {VERSION:<20} ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # Step 1: Clean
    print("▶ Step 1/4: Cleaning previous builds...")
    clean_build(dev)
    print("  Done")

    # Step 2: Build
    print("▶ Step 2/4: Building SageDLP.exe...")
    if not build_exe(dev, dirs):
        print("[FAILED] Build aborted")
        sys.exit(1)

    # Step 3: Assemble
    print("▶ Step 3/4: Assembling release...")
    if not assemble_release(dev, dirs):
        print("[FAILED] Assembly aborted")
        sys.exit(1)

    # Step 4: Installer
    print("▶ Step 4/4: Generating installer...")
    generate_installer(dev, dirs)

    print(f"\n{'='*60}")
    print(f"  ✓ Build complete!")
    print(f"  build/SageDLP.exe  – Single-file executable")
    if not dev:
        print(f"  build/SageDLP-v{VERSION}-Portable.zip  – Portable zip")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()