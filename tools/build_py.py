"""Build the Python edition for Windows: PyInstaller --onedir, a portable zip and an NSIS setup.

    python tools/build_py.py

Results in dist/python/: Calibrate3dPrinter/ (the folder), Calibrate3dPrinter-<v>-portable.zip
and Calibrate3dPrinter-<v>-setup.exe. The version comes from VERSION.
"""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = "Calibrate3dPrinter"
OUT = ROOT / "dist" / "python"
WORK = ROOT / "build" / "pyinstaller"
NSIS = [r"C:\Program Files (x86)\NSIS\makensis.exe", r"C:\Program Files\NSIS\makensis.exe"]
EXCLUDE = ["tkinter", "PIL", "numpy", "pytest", "hypothesis", "IPython", "matplotlib"]


def version():
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def pyinstaller():
    sep = os.pathsep
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
            "--name", APP, "--icon", str(ROOT / "assets" / "icon.ico"),
            "--paths", str(ROOT / "python"),
            "--add-data", f"{ROOT / 'profiles'}{sep}profiles",
            "--add-data", f"{ROOT / 'VERSION'}{sep}.",
            "--add-data", f"{ROOT / 'assets' / 'icon.png'}{sep}assets",
            "--distpath", str(OUT), "--workpath", str(WORK), "--specpath", str(WORK)]
    for m in EXCLUDE:
        args += ["--exclude-module", m]
    args.append(str(ROOT / "python" / "calib3d" / "__main__.py"))
    subprocess.run(args, check=True, cwd=ROOT)


def trim(folder):
    """Drop what the window does not need: software OpenGL, PDF, Qt translations but ru."""
    qt = folder / "_internal" / "PySide6"
    doomed = [qt / "opengl32sw.dll", qt / "Qt6Pdf.dll", qt / "plugins" / "imageformats" / "qpdf.dll",
              qt / "Qt6Quick.dll", qt / "Qt6Qml.dll", qt / "Qt6QmlModels.dll", qt / "Qt6VirtualKeyboard.dll"]
    tr = qt / "translations"
    if tr.is_dir():
        doomed += [p for p in tr.iterdir() if not p.name.endswith("_ru.qm")]
    freed = 0
    for p in doomed:
        if p.is_file():
            freed += p.stat().st_size
            p.unlink()
    return freed


def portable(folder, v):
    (folder / "portable.txt").write_text(
        "While this file lies next to Calibrate3dPrinter.exe, settings and own profiles are kept in the\n"
        "'data' folder next to it, not in the user profile. Delete it to get the usual behaviour.\n"
        "Пока этот файл лежит рядом с exe, настройки и свои профили хранятся в папке data рядом.\n",
        encoding="utf-8")
    for doc in ("README.md", "README.ru.md", "LICENSE"):
        shutil.copy(ROOT / doc, folder / doc)
    z = OUT / f"{APP}-{v}-portable.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in folder.rglob("*"):
            zf.write(p, Path(APP) / p.relative_to(folder))
    return z


def setup(v):
    exe = next((p for p in NSIS if Path(p).exists()), None)
    if not exe:
        print("NSIS not found - no setup")
        return None
    subprocess.run([exe, f"/DVERSION={v}", f"/DSRC={OUT / APP}", f"/DOUT={OUT}",
                    f"/DICON={ROOT / 'assets' / 'icon.ico'}", str(ROOT / "tools" / "installer_py.nsi")],
                   check=True, cwd=ROOT)
    return OUT / f"{APP}-{v}-setup.exe"


def main():
    v = version()
    if OUT.exists():
        shutil.rmtree(OUT / APP, ignore_errors=True)   # our own build output only
    pyinstaller()
    folder = OUT / APP
    print(f"trimmed {trim(folder) / 1e6:.1f} MB")
    z = portable(folder, v)
    s = setup(v)
    print(z, s)


if __name__ == "__main__":
    main()
