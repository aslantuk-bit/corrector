# -*- mode: python ; coding: utf-8 -*-
# Сборка «Проверки запуска»: одна папка, без консоли. Запуск: pyinstaller --noconfirm sborka/launchcheck.spec
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "sborka" / "entry_launchcheck.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Проверка_запуска",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Проверка_запуска")
