# -*- mode: python ; coding: utf-8 -*-
# Сборка Корректора: одна папка, два исполняемых файла (окно без консоли и командная строка).
# Запуск: pyinstaller --noconfirm sborka/corrector.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parent
import docx as _docx

docx_templates = Path(_docx.__file__).parent / "templates"
datas = (collect_data_files("pymorphy3_dicts_ru") + collect_data_files("pymorphy3")
         + [(str(docx_templates), "docx/templates")])
hidden = collect_submodules("pymorphy3") + collect_submodules("kazsearch") + collect_submodules("spylls") + ["yaml"]

app = Analysis([str(root / "sborka" / "entry_corrector.py")], pathex=[str(root)], datas=datas, hiddenimports=hidden,
               excludes=["tkinter", "unittest", "pydoc", "pytest"], noarchive=False)
cli = Analysis([str(root / "sborka" / "entry_corrector_cli.py")], pathex=[str(root)], datas=datas, hiddenimports=hidden,
               excludes=["tkinter", "unittest", "pydoc", "pytest"], noarchive=False)
MERGE((app, "Корректор", "Корректор"), (cli, "Корректор-cli", "Корректор-cli"))

app_pyz = PYZ(app.pure)
app_exe = EXE(app_pyz, app.scripts, [], exclude_binaries=True, name="Корректор", debug=False, strip=False, upx=False, console=False)
cli_pyz = PYZ(cli.pure)
cli_exe = EXE(cli_pyz, cli.scripts, [], exclude_binaries=True, name="Корректор-cli", debug=False, strip=False, upx=False, console=True)
coll = COLLECT(app_exe, app.binaries, app.datas, cli_exe, cli.binaries, cli.datas, strip=False, upx=False, name="Корректор")
