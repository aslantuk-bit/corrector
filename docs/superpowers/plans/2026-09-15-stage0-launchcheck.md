# Этап 0 «Нулевая сборка» — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Репозиторий, окружение на Mac, переносная программа `Проверка_запуска.exe` с приложенной Java, сборщик GitHub, который выдаёт готовый архив для флешки, и виртуальная Windows для проверки глазами.

**Architecture:** Маленький пакет `launchcheck` (пробы системы → текстовый отчёт → окно PySide6 или режим без окна), общие для всего проекта скрипты поставки в `sborka/` (скачивание артефактов по зафиксированным адресам с SHA-256, спецификация PyInstaller, сборка папки поставки и архива) и workflow GitHub Actions на Windows, который тестирует, собирает, запускает собранную программу и публикует архив.

**Tech Stack:** Python 3.13, PySide6-Essentials 6.11.2, pytest 9.1.1, pytest-qt 4.5.0, PyInstaller 6.22.3, uv, Temurin JRE 21.0.12.1+1, GitHub Actions (windows-latest), UTM + CrystalFetch на Mac.

**Spec:** `docs/superpowers/specs/2026-09-15-corrector-design.md` (разделы 2, 11, 13, 15 — этап 0).

## Global Constraints

- Python 3.13 и для разработки на Mac, и для сборки на Windows (спецификация, раздел 12).
- Программа лежит в одной папке, запускается двойным щелчком, ничего не устанавливает, в сеть не ходит, прав администратора не требует (раздел 2).
- Все скачивания в сборке — только по зафиксированным адресам с контрольными суммами SHA-256 (раздел 12, файл `sborka/artifacts.lock`; в спецификации папка названа `build/`, но PyInstaller использует `build/` под свои рабочие файлы, поэтому папка скриптов поставки — `sborka/`).
- Исполняемый файл и папка поставки — с кириллическим именем `Проверка_запуска`; архив — с латинским именем `proverka-zapuska-<версия>-win64.zip`. Если PyInstaller на сборщике не справится с кириллическим именем, откат — `launchcheck.exe`, и это фиксируется в README.
- Тексты для пользователя — по-русски, без англицизмов; отчёт сохраняется в UTF-8 с BOM, чтобы Блокнот показывал кириллицу.
- Оригинальные файлы пользователя никогда не изменяются (в этом этапе программа вообще не читает чужих файлов).
- Разработка через тесты: сначала падающий тест, потом код. Коммит после каждой задачи. Автор коммитов настраивается локально в репозитории (`git config user.name/user.email`), глобальной настройки на Mac нет.

---

## Структура файлов

```
corrector/
  pyproject.toml                  метаданные, настройки pytest (pythonpath ".", qt_api pyside6)
  requirements.txt                PySide6-Essentials==6.11.2
  requirements-dev.txt            -r requirements.txt, pytest, pytest-qt, pyinstaller
  .gitignore                      .venv/, vendor/, dist/, build/, __pycache__/, *.pyc, .pytest_cache/
  README.md                       что это, как поставить окружение, как собрать, где взять архив
  tools/dev_setup.sh              venv через uv, зависимости, JRE для Mac в vendor/
  launchcheck/
    __init__.py                   __version__ = "0.1.0"
    probes.py                     пробы системы: os_info, memory_gb, drive_kind, write_test, java_version, cpu_count, free_disk_gb, app_dir, default_java, qt_version
    report.py                     run_all(base_dir, java_exe) -> dict; build_report(dict) -> str; save_report(text, base_dir) -> Path
    app.py                        main(argv) -> int: разбор аргументов, пробы, отчёт, окно или режим без окна
    window.py                     ReportWindow(text, base_dir); show(text, base_dir) -> int
    __main__.py                   python -m launchcheck
  sborka/
    artifacts.lock                JSON: имя → url, sha256, size, unpack_root, inner (необязательно), note
    fetch_artifacts.py            load_lock, sha256_of, download, unpack, fetch(name, entry, vendor), main
    entry_launchcheck.py          точка входа для PyInstaller
    launchcheck.spec              спецификация PyInstaller: одна папка, без консоли, имя Проверка_запуска
    assemble.py                   assemble(app_name, version, dist, vendor, jre, instruction, zip_name) -> Path
    ИНСТРУКЦИЯ-проверка-запуска.txt
  .github/workflows/windows.yml   тесты → JRE → PyInstaller → сборка папки → запуск собранной программы → артефакт → релиз по тэгу
  docs/vm-setup.md                виртуальная Windows 11 ARM в UTM: пошагово, что делает автор руками
  docs/acceptance-stage0.md       что должен сделать коллега на рабочем ПК и что прислать
  tests/
    __init__.py                   обязателен: иначе tests/launchcheck затеняет пакет launchcheck
    conftest.py                   QT_QPA_PLATFORM=offscreen до импорта Qt
    launchcheck/conftest.py       make_fake_java(directory, exit_code, sleep) -> Path
    launchcheck/test_probes.py
    launchcheck/test_report.py
    launchcheck/test_app.py
    launchcheck/test_window.py
    sborka/test_fetch_artifacts.py
    sborka/test_assemble.py
```

---

### Task 1: Каркас репозитория и окружение

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `README.md`, `tools/dev_setup.sh`, `tests/conftest.py`, `launchcheck/__init__.py`, `tests/__init__.py`, `tests/launchcheck/__init__.py`, `tests/sborka/__init__.py` (все три пустые)

**Interfaces:**
- Produces: `launchcheck.__version__ == "0.1.0"`; команда `.venv/bin/python -m pytest -q` работает; `import PySide6` работает в `.venv`.

- [ ] **Step 1: Настроить автора коммитов и написать файлы каркаса**

```bash
cd ~/corrector
git config user.name "aslantuk"
git config user.email "aslantuk@gmail.com"
```

`pyproject.toml`:
```toml
[project]
name = "corrector"
version = "0.1.0"
description = "Корректор: проверка орфографии, пунктуации и стиля юридических текстов (ru/kk) с флешки"
requires-python = ">=3.13,<3.14"
dependencies = ["PySide6-Essentials==6.11.2"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
qt_api = "pyside6"
```

`requirements.txt`:
```
PySide6-Essentials==6.11.2
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest==9.1.1
pytest-qt==4.5.0
pyinstaller==6.22.3
```

`.gitignore`:
```
.venv/
vendor/
dist/
build/
__pycache__/
*.pyc
.pytest_cache/
*.spec.bak
```

`launchcheck/__init__.py`:
```python
"""Проверка запуска: пробная программа, которая показывает, запускается ли переносная сборка на рабочем ПК."""

__version__ = "0.1.0"
```

`tests/conftest.py`:
```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

`tools/dev_setup.sh`:
```bash
#!/bin/zsh
# Окружение разработчика на Mac: venv на Python 3.13 через uv, зависимости, JRE для тестов.
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python sborka/fetch_artifacts.py jre-mac-aarch64
echo "Готово. Тесты: .venv/bin/python -m pytest -q"
```
(`chmod +x tools/dev_setup.sh`; скрипт `sborka/fetch_artifacts.py` появится в задаче 6 — до этого последнюю строку выполнять не нужно.)

`README.md`:
```markdown
# Корректор

Проверка орфографии, пунктуации и стиля юридических текстов на русском и казахском.
Работает с флешки на Windows без установки и без интернета. Спецификация:
`docs/superpowers/specs/2026-09-15-corrector-design.md`.

## Этап 0: «Проверка запуска»

Пробная программа `Проверка_запуска.exe` с приложенной Java. Показывает, запускается ли
переносная сборка на рабочем ПК, и пишет `отчёт_запуска.txt`.

## Окружение на Mac

    tools/dev_setup.sh
    .venv/bin/python -m pytest -q

## Сборка

Собирает GitHub Actions (`.github/workflows/windows.yml`) при каждом пуше в `main`:
архив `proverka-zapuska-<версия>-win64.zip` лежит в артефактах запуска, а при тэге `v*` —
в релизе. Локально на Mac: `pyinstaller --noconfirm sborka/launchcheck.spec` и
`python sborka/assemble.py launchcheck` (получится сборка для Mac, для проверки скриптов).
```

- [ ] **Step 2: Создать окружение и убедиться, что pytest и PySide6 работают**

Run:
```bash
cd ~/corrector && uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -c "import PySide6, sys; print(sys.version.split()[0], PySide6.__version__)"
.venv/bin/python -m pytest -q
```
Expected: `3.13.x 6.11.2`; pytest сообщает `no tests ran` без ошибок импорта.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Каркас репозитория: окружение Python 3.13, зависимости, настройки pytest"
```

---

### Task 2: Пробы системы (`launchcheck/probes.py`)

**Files:**
- Create: `launchcheck/probes.py`, `tests/launchcheck/conftest.py`, `tests/launchcheck/test_probes.py`

**Interfaces:**
- Produces:
  - `os_info() -> str` — «Windows 10.0 сборка 22631 (AMD64)» или «Darwin 25.6.0 (arm64)».
  - `memory_gb() -> float | None`, `cpu_count() -> int`, `free_disk_gb(path: Path) -> float`.
  - `drive_kind(path: Path) -> str` — «съёмный (флешка)», «жёсткий диск», …, «не Windows».
  - `write_test(directory: Path) -> bool`.
  - `java_version(java_exe: Path, timeout: float = 60.0) -> tuple[bool, str]`.
  - `qt_version() -> str` — версия PySide6 или текст ошибки импорта.
  - `app_dir() -> Path` — папка программы (рядом с exe в сборке, текущая папка при запуске из исходников).
  - `default_java(base_dir: Path) -> Path` — `base_dir/java/bin/java.exe` на Windows, `base_dir/java/bin/java` иначе.
  - `tests/launchcheck/conftest.py`: `make_fake_java(directory: Path, exit_code: int = 0, sleep: float = 0) -> Path`.

- [ ] **Step 1: Написать помощник и падающие тесты**

`tests/launchcheck/conftest.py`:
```python
import sys
from pathlib import Path


def make_fake_java(directory: Path, exit_code: int = 0, sleep: float = 0) -> Path:
    """Поддельная java: печатает строку версии в stderr, как настоящая, и выходит с нужным кодом."""
    if sys.platform == "win32":
        path = directory / "java.bat"
        wait = f"ping -n {int(sleep) + 1} 127.0.0.1 >nul\r\n" if sleep else ""  # timeout не работает без консоли
        path.write_text(
            "@echo off\r\n" + wait + '>&2 echo openjdk version "21.0.12.1"\r\n' + f"exit /b {exit_code}\r\n"
        )
    else:
        path = directory / "java"
        path.write_text(
            f"#!/bin/sh\nsleep {sleep}\necho 'openjdk version \"21.0.12.1\"' >&2\nexit {exit_code}\n"
        )
        path.chmod(0o755)
    return path
```

`tests/launchcheck/test_probes.py`:
```python
import os
import platform
import sys
from pathlib import Path

import pytest

from launchcheck import probes
from tests.launchcheck.conftest import make_fake_java


def test_os_info_names_the_system():
    text = probes.os_info()
    assert ("Windows" in text) or (platform.system() in text)
    assert platform.machine() in text


def test_memory_gb_is_positive_or_unknown():
    value = probes.memory_gb()
    assert value is None or value > 0


def test_cpu_count_positive():
    assert probes.cpu_count() >= 1


def test_free_disk_gb_positive(tmp_path):
    assert probes.free_disk_gb(tmp_path) > 0


def test_write_test_true_in_writable_dir(tmp_path):
    assert probes.write_test(tmp_path) is True
    assert list(tmp_path.iterdir()) == []  # временный файл удалён


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="права каталога не действуют")
def test_write_test_false_in_readonly_dir(tmp_path):
    tmp_path.chmod(0o500)
    try:
        assert probes.write_test(tmp_path) is False
    finally:
        tmp_path.chmod(0o700)


@pytest.mark.skipif(sys.platform == "win32", reason="на Windows тип диска настоящий")
def test_drive_kind_outside_windows(tmp_path):
    assert probes.drive_kind(tmp_path) == "не Windows"


def test_java_version_missing_file(tmp_path):
    ok, text = probes.java_version(tmp_path / "java")
    assert ok is False
    assert text.startswith("файл не найден")


def test_java_version_ok(tmp_path):
    ok, text = probes.java_version(make_fake_java(tmp_path))
    assert ok is True
    assert text == 'openjdk version "21.0.12.1"'


def test_java_version_nonzero_exit(tmp_path):
    ok, text = probes.java_version(make_fake_java(tmp_path, exit_code=3))
    assert ok is False
    assert "21.0.12.1" in text


def test_java_version_timeout(tmp_path):
    ok, text = probes.java_version(make_fake_java(tmp_path, sleep=3), timeout=0.5)
    assert ok is False
    assert text == "не ответила за 0.5 с"


def test_qt_version_is_pyside_version():
    import PySide6

    assert probes.qt_version() == PySide6.__version__


def test_app_dir_from_sources_is_cwd():
    assert probes.app_dir() == Path.cwd()


def test_default_java_path(tmp_path):
    expected = tmp_path / "java" / "bin" / ("java.exe" if sys.platform == "win32" else "java")
    assert probes.default_java(tmp_path) == expected
```

- [ ] **Step 2: Запустить тесты и убедиться, что они падают**

Run: `.venv/bin/python -m pytest tests/launchcheck/test_probes.py -q`
Expected: ошибки `ModuleNotFoundError: No module named 'launchcheck.probes'`.

- [ ] **Step 3: Написать пробы**

`launchcheck/probes.py`:
```python
"""Пробы системы. Каждая функция отвечает на один вопрос и не падает: неизвестное значение — None или текст."""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DRIVE_KINDS = {
    0: "неизвестно",
    1: "нет корневого каталога",
    2: "съёмный (флешка)",
    3: "жёсткий диск",
    4: "сетевой",
    5: "CD/DVD",
    6: "RAM-диск",
}


def os_info() -> str:
    if sys.platform == "win32":
        v = sys.getwindowsversion()
        return f"Windows {v.major}.{v.minor} сборка {v.build} ({platform.machine()})"
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def memory_gb() -> float | None:
    if sys.platform == "win32":
        return _memory_gb_windows()
    if sys.platform == "darwin":
        out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout.strip()
        return round(int(out) / 1024**3, 1) if out.isdigit() else None
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 1)
    except (ValueError, OSError):
        return None


def _memory_gb_windows() -> float | None:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return round(status.ullTotalPhys / 1024**3, 1)
    return None


def cpu_count() -> int:
    return os.cpu_count() or 0


def free_disk_gb(path: Path) -> float:
    return round(shutil.disk_usage(path).free / 1024**3, 1)


def drive_kind(path: Path) -> str:
    if sys.platform != "win32":
        return "не Windows"
    root = os.path.splitdrive(str(path.resolve()))[0] + "\\"
    return DRIVE_KINDS.get(ctypes.windll.kernel32.GetDriveTypeW(root), "неизвестно")


def write_test(directory: Path) -> bool:
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix="~проверка-записи-", delete=True):
            pass
        return True
    except OSError:
        return False


def java_version(java_exe: Path, timeout: float = 60.0) -> tuple[bool, str]:
    if not java_exe.exists():
        return False, f"файл не найден: {java_exe}"
    try:
        result = subprocess.run(
            [str(java_exe), "-version"], capture_output=True, text=True, timeout=timeout, **_no_window()
        )
    except subprocess.TimeoutExpired:
        return False, f"не ответила за {timeout:g} с"
    except OSError as error:
        return False, f"не запустилась: {error}"
    text = (result.stderr or result.stdout).strip()
    first_line = text.splitlines()[0] if text else f"код возврата {result.returncode}"
    return result.returncode == 0, first_line


def _no_window() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def qt_version() -> str:
    try:
        import PySide6

        return PySide6.__version__
    except Exception as error:  # noqa: BLE001 — любая ошибка импорта должна попасть в отчёт
        return f"не загрузился: {error}"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def default_java(base_dir: Path) -> Path:
    return base_dir / "java" / "bin" / ("java.exe" if sys.platform == "win32" else "java")
```

- [ ] **Step 4: Запустить тесты**

Run: `.venv/bin/python -m pytest tests/launchcheck/test_probes.py -q`
Expected: все проходят (тест только для Windows пропущен).

- [ ] **Step 5: Commit**

```bash
git add launchcheck/probes.py tests/launchcheck && git commit -m "Проверка запуска: пробы системы (ОС, память, диск, запись, Java, Qt)"
```

---

### Task 3: Отчёт (`launchcheck/report.py`)

**Files:**
- Create: `launchcheck/report.py`, `tests/launchcheck/test_report.py`

**Interfaces:**
- Consumes: `launchcheck.probes.*`, `make_fake_java`.
- Produces:
  - `run_all(base_dir: Path, java_exe: Path | None = None) -> dict[str, object]` с ключами `версия, время, папка, система, память_гб, процессоры, диск, свободно_гб, запись, qt, java_ok, java, java_путь`.
  - `build_report(results: dict[str, object]) -> str` — многострочный текст, последняя строка начинается с `ИТОГ:`.
  - `save_report(text: str, base_dir: Path) -> Path` — пишет `отчёт_запуска.txt` в UTF-8 с BOM в `base_dir`, иначе на рабочий стол, иначе в домашнюю папку; `OSError`, если никуда.
  - `REPORT_NAME = "отчёт_запуска.txt"`, `OK_LINE = "ИТОГ: всё работает"`.

- [ ] **Step 1: Падающие тесты**

`tests/launchcheck/test_report.py`:
```python
import sys
from pathlib import Path

import pytest

from launchcheck import __version__, report
from tests.launchcheck.conftest import make_fake_java


def sample(java_ok=True):
    return {
        "версия": "0.1.0",
        "время": "15.09.2026 12:00",
        "папка": "E:\\Проверка_запуска",
        "система": "Windows 10.0 сборка 19045 (AMD64)",
        "память_гб": 7.9,
        "процессоры": 4,
        "диск": "съёмный (флешка)",
        "свободно_гб": 12.3,
        "запись": True,
        "qt": "6.11.2",
        "java_ok": java_ok,
        "java": 'openjdk version "21.0.12.1"' if java_ok else "файл не найден: E:\\java\\bin\\java.exe",
        "java_путь": "E:\\Проверка_запуска\\java\\bin\\java.exe",
    }


def test_build_report_lists_every_value():
    text = report.build_report(sample())
    for piece in ["0.1.0", "15.09.2026 12:00", "E:\\Проверка_запуска", "сборка 19045", "7.9 ГБ", "4",
                  "съёмный (флешка)", "12.3 ГБ", "Запись в папку программы: да", "Qt: 6.11.2",
                  'Java: OK — openjdk version "21.0.12.1"']:
        assert piece in text
    assert text.rstrip().splitlines()[-1] == report.OK_LINE


def test_build_report_failure_summary():
    text = report.build_report(sample(java_ok=False))
    assert "Java: ОШИБКА — файл не найден" in text
    assert text.rstrip().splitlines()[-1] == "ИТОГ: Java не запустилась — пришлите этот отчёт автору"


def test_build_report_unknown_memory():
    data = sample()
    data["память_гб"] = None
    assert "Память: неизвестно" in report.build_report(data)


def test_run_all_with_fake_java(tmp_path):
    results = report.run_all(tmp_path, java_exe=make_fake_java(tmp_path))
    assert results["версия"] == __version__
    assert results["java_ok"] is True
    assert results["папка"] == str(tmp_path)
    assert results["запись"] is True
    assert set(results) == {"версия", "время", "папка", "система", "память_гб", "процессоры", "диск",
                            "свободно_гб", "запись", "qt", "java_ok", "java", "java_путь"}


def test_run_all_default_java_path(tmp_path):
    results = report.run_all(tmp_path)
    assert results["java_путь"] == str(tmp_path / "java" / "bin" / ("java.exe" if sys.platform == "win32" else "java"))
    assert results["java_ok"] is False


def test_save_report_writes_utf8_bom(tmp_path):
    path = report.save_report("Проверка\n", tmp_path)
    assert path == tmp_path / report.REPORT_NAME
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert path.read_text(encoding="utf-8-sig") == "Проверка\n"


def test_save_report_falls_back_to_desktop(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    path = report.save_report("x", tmp_path / "нет-такой-папки")
    assert path == home / "Desktop" / report.REPORT_NAME


def test_save_report_raises_when_nowhere(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "нет-дома"))
    with pytest.raises(OSError):
        report.save_report("x", tmp_path / "нет-такой-папки")
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/python -m pytest tests/launchcheck/test_report.py -q`
Expected: `ModuleNotFoundError: No module named 'launchcheck.report'`.

- [ ] **Step 3: Написать отчёт**

`launchcheck/report.py`:
```python
"""Сбор проб в один словарь и текст отчёта, который пользователь пришлёт автору."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from launchcheck import __version__, probes

REPORT_NAME = "отчёт_запуска.txt"
OK_LINE = "ИТОГ: всё работает"
FAIL_LINE = "ИТОГ: Java не запустилась — пришлите этот отчёт автору"


def run_all(base_dir: Path, java_exe: Path | None = None) -> dict[str, object]:
    java_exe = java_exe or probes.default_java(base_dir)
    java_ok, java_text = probes.java_version(java_exe)
    return {
        "версия": __version__,
        "время": dt.datetime.now().strftime("%d.%m.%Y %H:%M"),
        "папка": str(base_dir),
        "система": probes.os_info(),
        "память_гб": probes.memory_gb(),
        "процессоры": probes.cpu_count(),
        "диск": probes.drive_kind(base_dir),
        "свободно_гб": probes.free_disk_gb(base_dir),
        "запись": probes.write_test(base_dir),
        "qt": probes.qt_version(),
        "java_ok": java_ok,
        "java": java_text,
        "java_путь": str(java_exe),
    }


def build_report(results: dict[str, object]) -> str:
    r = results
    lines = [
        f"Проверка запуска Корректора, версия {r['версия']}",
        f"Время: {r['время']}",
        f"Папка программы: {r['папка']}",
        f"Система: {r['система']}",
        f"Память: {_gb(r['память_гб'])}",
        f"Процессоры: {r['процессоры']}",
        f"Диск: {r['диск']}, свободно {_gb(r['свободно_гб'])}",
        f"Запись в папку программы: {'да' if r['запись'] else 'нет'}",
        f"Qt: {r['qt']}",
        f"Java: {'OK' if r['java_ok'] else 'ОШИБКА'} — {r['java']}",
        f"Путь к Java: {r['java_путь']}",
        "",
        OK_LINE if r["java_ok"] else FAIL_LINE,
    ]
    return "\n".join(lines) + "\n"


def _gb(value: object) -> str:
    return "неизвестно" if value is None else f"{value} ГБ"


def save_report(text: str, base_dir: Path) -> Path:
    errors = []
    for folder in (base_dir, Path.home() / "Desktop", Path.home()):
        path = folder / REPORT_NAME
        try:
            path.write_text(text, encoding="utf-8-sig")
            return path
        except OSError as error:
            errors.append(f"{folder}: {error}")
    raise OSError("не удалось сохранить отчёт: " + "; ".join(errors))
```

- [ ] **Step 4: Запустить тесты**

Run: `.venv/bin/python -m pytest tests/launchcheck -q`
Expected: все проходят.

- [ ] **Step 5: Commit**

```bash
git add launchcheck/report.py tests/launchcheck/test_report.py && git commit -m "Проверка запуска: сбор проб и текст отчёта"
```

---

### Task 4: Точка входа и режим без окна (`launchcheck/app.py`)

**Files:**
- Create: `launchcheck/app.py`, `launchcheck/__main__.py`, `tests/launchcheck/test_app.py`

**Interfaces:**
- Consumes: `report.run_all`, `report.build_report`, `report.save_report`, `probes.app_dir`, `window.show` (задача 5; здесь импортируется лениво и только вне режима без окна).
- Produces: `main(argv: list[str] | None = None) -> int`. Аргументы: `--report-only` (без окна), `--out ПАПКА` (куда писать отчёт), `--java ПУТЬ`. Код возврата: 0 — Java запустилась, 1 — нет. В отчёт добавляется строка `Отчёт сохранён: <путь>` или `Отчёт не сохранён: <причина>`.

- [ ] **Step 1: Падающие тесты**

`tests/launchcheck/test_app.py`:
```python
from launchcheck import app, report
from tests.launchcheck.conftest import make_fake_java


def test_report_only_writes_file_and_returns_zero(tmp_path, capsys):
    java = make_fake_java(tmp_path)
    out = tmp_path / "отчёт"
    out.mkdir()
    code = app.main(["--report-only", "--out", str(out), "--java", str(java)])
    assert code == 0
    text = (out / report.REPORT_NAME).read_text(encoding="utf-8-sig")
    assert "Java: OK" in text
    assert report.OK_LINE in text
    assert f"Отчёт сохранён: {out / report.REPORT_NAME}" in capsys.readouterr().out


def test_report_only_missing_java_returns_one(tmp_path):
    code = app.main(["--report-only", "--out", str(tmp_path), "--java", str(tmp_path / "нет" / "java")])
    assert code == 1
    assert "Java: ОШИБКА" in (tmp_path / report.REPORT_NAME).read_text(encoding="utf-8-sig")


def test_window_mode_calls_show(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("launchcheck.window.show", lambda text, base_dir: calls.append((text, base_dir)) or 0)
    code = app.main(["--out", str(tmp_path), "--java", str(make_fake_java(tmp_path))])
    assert code == 0
    assert len(calls) == 1
    assert "Java: OK" in calls[0][0]
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/python -m pytest tests/launchcheck/test_app.py -q`
Expected: `ModuleNotFoundError: No module named 'launchcheck.app'`.

- [ ] **Step 3: Написать точку входа**

`launchcheck/app.py`:
```python
"""Точка входа: пробы → отчёт → файл → окно (или только файл в режиме --report-only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from launchcheck import probes, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="launchcheck", description="Проверка запуска переносной сборки")
    parser.add_argument("--report-only", action="store_true", help="без окна: записать отчёт и выйти")
    parser.add_argument("--out", type=Path, help="папка для отчёта (по умолчанию папка программы)")
    parser.add_argument("--java", type=Path, help="путь к java (по умолчанию java/bin/java.exe рядом с программой)")
    args = parser.parse_args(argv)

    base_dir = probes.app_dir()
    results = report.run_all(base_dir, java_exe=args.java)
    text = report.build_report(results)
    try:
        path = report.save_report(text, args.out or base_dir)
        text += f"Отчёт сохранён: {path}\n"
    except OSError as error:
        text += f"Отчёт не сохранён: {error}\n"

    if args.report_only:
        if sys.stdout is not None:  # в сборке без консоли stdout отсутствует
            sys.stdout.write(text)
        return 0 if results["java_ok"] else 1

    from launchcheck import window

    window.show(text, base_dir)
    return 0 if results["java_ok"] else 1
```

`launchcheck/__main__.py`:
```python
import sys

from launchcheck.app import main

sys.exit(main())
```

Тест `test_window_mode_calls_show` требует модуль `launchcheck.window` — до задачи 5 положить заглушку `launchcheck/window.py`:
```python
"""Окно отчёта (заполняется в задаче 5)."""

from pathlib import Path


def show(text: str, base_dir: Path) -> int:
    raise NotImplementedError
```

- [ ] **Step 4: Запустить тесты**

Run: `.venv/bin/python -m pytest tests/launchcheck -q`
Expected: все проходят.

- [ ] **Step 5: Commit**

```bash
git add launchcheck/app.py launchcheck/__main__.py launchcheck/window.py tests/launchcheck/test_app.py && git commit -m "Проверка запуска: точка входа, режим без окна, коды возврата"
```

---

### Task 5: Окно отчёта (`launchcheck/window.py`)

**Files:**
- Modify: `launchcheck/window.py` (заменить заглушку)
- Create: `tests/launchcheck/test_window.py`

**Interfaces:**
- Consumes: `report.OK_LINE`.
- Produces: класс `ReportWindow(text: str, base_dir: Path)` с атрибутами `headline: QLabel`, `view: QPlainTextEdit`, `copy_button: QPushButton`, `close_button: QPushButton`; `show(text, base_dir) -> int` создаёт `QApplication` (если нет), показывает окно, возвращает код `app.exec()`.

- [ ] **Step 1: Падающие тесты**

`tests/launchcheck/test_window.py`:
```python
from pathlib import Path

from PySide6.QtWidgets import QApplication

from launchcheck import report
from launchcheck.window import ReportWindow


def test_window_shows_report_and_success_headline(qtbot):
    text = "Java: OK — openjdk\n\n" + report.OK_LINE + "\nОтчёт сохранён: E:\\отчёт_запуска.txt\n"
    window = ReportWindow(text, Path("E:/"))
    qtbot.addWidget(window)
    assert window.windowTitle() == "Проверка запуска Корректора"
    assert window.headline.text() == "Всё запустилось. Пришлите автору файл отчёт_запуска.txt"
    assert window.view.toPlainText() == text
    assert window.view.isReadOnly()


def test_window_failure_headline(qtbot):
    window = ReportWindow("Java: ОШИБКА — файл не найден\n\n" + report.FAIL_LINE + "\n", Path("E:/"))
    qtbot.addWidget(window)
    assert window.headline.text() == "Есть проблема. Пришлите автору файл отчёт_запуска.txt"


def test_copy_button_puts_text_on_clipboard(qtbot):
    text = "строка отчёта\n" + report.OK_LINE + "\n"
    window = ReportWindow(text, Path("E:/"))
    qtbot.addWidget(window)
    window.copy_button.click()
    assert QApplication.clipboard().text() == text
    assert window.headline.text() == "Отчёт скопирован — вставьте его в сообщение автору"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/python -m pytest tests/launchcheck/test_window.py -q`
Expected: `ImportError: cannot import name 'ReportWindow'`.

- [ ] **Step 3: Написать окно**

`launchcheck/window.py`:
```python
"""Окно с отчётом: заголовок-вывод, текст, кнопки «Скопировать» и «Закрыть»."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from launchcheck import report

SUCCESS = "Всё запустилось. Пришлите автору файл отчёт_запуска.txt"
FAILURE = "Есть проблема. Пришлите автору файл отчёт_запуска.txt"
COPIED = "Отчёт скопирован — вставьте его в сообщение автору"


class ReportWindow(QMainWindow):
    def __init__(self, text: str, base_dir: Path) -> None:
        super().__init__()
        self.text = text
        self.base_dir = base_dir
        self.setWindowTitle("Проверка запуска Корректора")
        self.resize(760, 520)

        self.headline = QLabel(SUCCESS if report.OK_LINE in text else FAILURE)
        self.headline.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        self.view = QPlainTextEdit(text)
        self.view.setReadOnly(True)
        self.copy_button = QPushButton("Скопировать")
        self.copy_button.clicked.connect(self.copy_report)
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.headline)
        layout.addWidget(self.view)
        layout.addLayout(buttons)
        self.setCentralWidget(central)

    def copy_report(self) -> None:
        QApplication.clipboard().setText(self.text)
        self.headline.setText(COPIED)


def show(text: str, base_dir: Path) -> int:
    app = QApplication.instance() or QApplication([])
    window = ReportWindow(text, base_dir)
    window.show()
    return app.exec()
```

- [ ] **Step 4: Запустить тесты и посмотреть окно вживую**

Run: `.venv/bin/python -m pytest tests/launchcheck -q`
Expected: все проходят.

Run (окно на Mac, Java пока нет — ожидается заголовок «Есть проблема»): `.venv/bin/python -m launchcheck --out /tmp` → окно открывается, закрыть кнопкой; в `/tmp/отчёт_запуска.txt` есть строки «Система: Darwin …», «Qt: 6.11.2», «Java: ОШИБКА — файл не найден».

- [ ] **Step 5: Commit**

```bash
git add launchcheck/window.py tests/launchcheck/test_window.py && git commit -m "Проверка запуска: окно отчёта с кнопкой «Скопировать»"
```

---

### Task 6: Скачивание артефактов по замку (`sborka/artifacts.lock`, `sborka/fetch_artifacts.py`)

**Files:**
- Create: `sborka/__init__.py` (пустой), `sborka/artifacts.lock`, `sborka/fetch_artifacts.py`, `tests/sborka/test_fetch_artifacts.py`

**Interfaces:**
- Produces:
  - `load_lock(path: Path = LOCK) -> dict[str, dict]`.
  - `sha256_of(path: Path) -> str`.
  - `fetch(name: str, entry: dict, vendor: Path = VENDOR) -> Path` — скачивает `entry["url"]` в `vendor/_cache/`, сверяет SHA-256, распаковывает папку `entry["unpack_root"]` (и вложенную `entry["inner"]`, если есть) в `vendor/<name>/`, пишет метку `vendor/<name>/.artifact-sha256`; при совпадающей метке ничего не делает; при несовпадении суммы — `ValueError`.
  - Командная строка: `python sborka/fetch_artifacts.py jre-windows-x64 [jre-mac-aarch64] [--vendor ПАПКА]`.
  - Имена в замке: `jre-windows-x64` (Temurin 21.0.12.1+1, zip), `jre-mac-aarch64` (tar.gz, `inner = Contents/Home`).

- [ ] **Step 1: Замок и падающие тесты**

`sborka/artifacts.lock`:
```json
{
  "jre-windows-x64": {
    "url": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jre_x64_windows_hotspot_21.0.12.1_1.zip",
    "sha256": "d35f31e712f0fcf6ac5a093edc90204fbff22f720ba3950bd09d331d5e621636",
    "size": 48999141,
    "unpack_root": "jdk-21.0.12.1+1-jre",
    "note": "Temurin JRE 21.0.12.1+1 для Windows x64, лицензия GPL-2.0 с Classpath Exception"
  },
  "jre-mac-aarch64": {
    "url": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jre_aarch64_mac_hotspot_21.0.12.1_1.tar.gz",
    "sha256": "dec50fc6f9fcd4fe3ae8cabf5a5fa68f6afc48841f7698e468e9aa5d54beed84",
    "size": 48144965,
    "unpack_root": "jdk-21.0.12.1+1-jre",
    "inner": "Contents/Home",
    "note": "Temurin JRE 21.0.12.1+1 для Mac Apple Silicon, только для разработки и тестов"
  }
}
```

`tests/sborka/test_fetch_artifacts.py`:
```python
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from sborka import fetch_artifacts as fa


def make_zip(path: Path, files: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_targz(path: Path, files: dict[str, bytes]) -> str:
    with tarfile.open(path, "w:gz") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lock_file_has_both_jres():
    lock = fa.load_lock()
    assert set(lock) >= {"jre-windows-x64", "jre-mac-aarch64"}
    for entry in lock.values():
        assert len(entry["sha256"]) == 64
        assert entry["url"].startswith("https://")
        assert entry["unpack_root"]


def test_sha256_of(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")
    assert fa.sha256_of(f) == hashlib.sha256(b"abc").hexdigest()


def test_fetch_zip_unpacks_root_and_writes_stamp(tmp_path):
    archive = tmp_path / "jre.zip"
    digest = make_zip(archive, {"root-1/bin/java.exe": b"java", "root-1/release": b"JAVA_VERSION=21"})
    entry = {"url": archive.as_uri(), "sha256": digest, "unpack_root": "root-1"}
    target = fa.fetch("jre-test", entry, vendor=tmp_path / "vendor")
    assert target == tmp_path / "vendor" / "jre-test"
    assert (target / "bin" / "java.exe").read_bytes() == b"java"
    assert (target / ".artifact-sha256").read_text() == digest


def test_fetch_targz_with_inner_folder(tmp_path):
    archive = tmp_path / "jre.tar.gz"
    digest = make_targz(archive, {"root-1/Contents/Home/bin/java": b"java"})
    entry = {"url": archive.as_uri(), "sha256": digest, "unpack_root": "root-1", "inner": "Contents/Home"}
    target = fa.fetch("jre-mac", entry, vendor=tmp_path / "vendor")
    assert (target / "bin" / "java").read_bytes() == b"java"


def test_fetch_rejects_wrong_checksum(tmp_path):
    archive = tmp_path / "jre.zip"
    make_zip(archive, {"root-1/bin/java.exe": b"java"})
    entry = {"url": archive.as_uri(), "sha256": "0" * 64, "unpack_root": "root-1"}
    with pytest.raises(ValueError, match="контрольная сумма"):
        fa.fetch("jre-bad", entry, vendor=tmp_path / "vendor")
    assert not (tmp_path / "vendor" / "jre-bad").exists()


def test_fetch_skips_when_stamp_matches(tmp_path):
    archive = tmp_path / "jre.zip"
    digest = make_zip(archive, {"root-1/bin/java.exe": b"java"})
    entry = {"url": archive.as_uri(), "sha256": digest, "unpack_root": "root-1"}
    vendor = tmp_path / "vendor"
    fa.fetch("jre-test", entry, vendor=vendor)
    archive.unlink()  # второй раз скачивать нечего — и не нужно
    assert fa.fetch("jre-test", entry, vendor=vendor) == vendor / "jre-test"


def test_main_unknown_name_returns_two(capsys):
    assert fa.main(["нет-такого"]) == 2
    assert "нет в artifacts.lock" in capsys.readouterr().err
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/python -m pytest tests/sborka/test_fetch_artifacts.py -q`
Expected: `ModuleNotFoundError: No module named 'sborka.fetch_artifacts'`.

- [ ] **Step 3: Написать скрипт**

`sborka/fetch_artifacts.py`:
```python
"""Скачивает сторонние артефакты по sborka/artifacts.lock, сверяет SHA-256 и распаковывает в vendor/<имя>/."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sborka" / "artifacts.lock"
VENDOR = ROOT / "vendor"
STAMP = ".artifact-sha256"


def load_lock(path: Path = LOCK) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def unpack(archive: Path, target: Path, unpack_root: str, inner: str | None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="unpack-", dir=target.parent))
    try:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)
        else:
            with tarfile.open(archive) as t:
                t.extractall(tmp, filter="data")
        source = tmp / unpack_root
        if inner:
            source = source / inner
        if not source.is_dir():
            raise FileNotFoundError(f"в архиве {archive.name} нет папки {unpack_root}/{inner or ''}")
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(source), str(target))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fetch(name: str, entry: dict, vendor: Path = VENDOR) -> Path:
    target = vendor / name
    stamp = target / STAMP
    if stamp.exists() and stamp.read_text().strip() == entry["sha256"]:
        return target
    cache = vendor / "_cache"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / entry["url"].rsplit("/", 1)[-1]
    if not archive.exists() or sha256_of(archive) != entry["sha256"]:
        download(entry["url"], archive)
    actual = sha256_of(archive)
    if actual != entry["sha256"]:
        archive.unlink(missing_ok=True)
        raise ValueError(f"{name}: контрольная сумма не совпала: {actual} вместо {entry['sha256']}")
    unpack(archive, target, entry["unpack_root"], entry.get("inner"))
    stamp.write_text(entry["sha256"])
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Скачать артефакты из artifacts.lock в vendor/")
    parser.add_argument("names", nargs="+", help="имена записей из artifacts.lock")
    parser.add_argument("--vendor", type=Path, default=VENDOR)
    args = parser.parse_args(argv)
    lock = load_lock()
    for name in args.names:
        if name not in lock:
            print(f"нет в artifacts.lock: {name}", file=sys.stderr)
            return 2
        print(f"{name} → {fetch(name, lock[name], args.vendor)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Запустить тесты, скачать JRE для Mac и проверить программу с настоящей Java**

Run: `.venv/bin/python -m pytest tests/sborka -q` — все проходят.

Run: `.venv/bin/python sborka/fetch_artifacts.py jre-mac-aarch64 && vendor/jre-mac-aarch64/bin/java -version`
Expected: `openjdk version "21.0.12.1" …`.

Run: `.venv/bin/python -m launchcheck --report-only --out /tmp --java vendor/jre-mac-aarch64/bin/java; echo "код $?"`
Expected: в выводе `Java: OK — openjdk version "21.0.12.1"`, `ИТОГ: всё работает`, `код 0`.

- [ ] **Step 5: Commit**

```bash
git add sborka/__init__.py sborka/artifacts.lock sborka/fetch_artifacts.py tests/sborka && git commit -m "Поставка: замок артефактов и скачивание с проверкой SHA-256 (Temurin JRE 21)"
```

---

### Task 7: Спецификация PyInstaller и сборка папки поставки (`sborka/launchcheck.spec`, `sborka/assemble.py`)

**Files:**
- Create: `sborka/entry_launchcheck.py`, `sborka/launchcheck.spec`, `sborka/assemble.py`, `sborka/ИНСТРУКЦИЯ-проверка-запуска.txt`, `tests/sborka/test_assemble.py`

**Interfaces:**
- Consumes: `launchcheck.app.main`, `launchcheck.__version__`, `vendor/jre-*` из задачи 6.
- Produces:
  - `assemble(app_name: str, version: str, dist: Path = ROOT / "dist", vendor: Path = ROOT / "vendor", jre: str = "jre-windows-x64", instruction: Path | None = None, zip_name: str | None = None) -> Path` — копирует `dist/<app_name>/` в `dist/bundle/<app_name>/`, кладёт рядом `java/` из `vendor/<jre>/` (без метки `.artifact-sha256`), `ИНСТРУКЦИЯ.txt`, и упаковывает в `dist/bundle/<zip_name>` с верхней папкой `<app_name>/`. Возвращает путь к архиву.
  - Командная строка: `python sborka/assemble.py launchcheck [--jre jre-mac-aarch64]` — для `launchcheck` имя папки `Проверка_запуска`, архив `proverka-zapuska-<версия>-win64.zip` (с `--jre jre-mac-aarch64` — `…-mac.zip`).
  - Реестр приложений `APPS = {"launchcheck": {"folder": "Проверка_запуска", "zip": "proverka-zapuska", "version": launchcheck.__version__, "instruction": ROOT / "sborka" / "ИНСТРУКЦИЯ-проверка-запуска.txt"}}`.

- [ ] **Step 1: Падающие тесты**

`tests/sborka/test_assemble.py`:
```python
import zipfile
from pathlib import Path

import pytest

from sborka import assemble as asm


def make_tree(root: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def test_assemble_builds_folder_and_zip(tmp_path):
    dist, vendor = tmp_path / "dist", tmp_path / "vendor"
    make_tree(dist / "Проверка_запуска", {"Проверка_запуска.exe": b"exe", "_internal/base.dll": b"dll"})
    make_tree(vendor / "jre-windows-x64", {"bin/java.exe": b"java", ".artifact-sha256": b"abc"})
    instruction = tmp_path / "инструкция.txt"
    instruction.write_text("Откройте программу", encoding="utf-8")

    zip_path = asm.assemble("Проверка_запуска", "0.1.0", dist=dist, vendor=vendor,
                            instruction=instruction, zip_name="proverka-zapuska-0.1.0-win64.zip")

    bundle = dist / "bundle" / "Проверка_запуска"
    assert (bundle / "Проверка_запуска.exe").read_bytes() == b"exe"
    assert (bundle / "_internal" / "base.dll").exists()
    assert (bundle / "java" / "bin" / "java.exe").read_bytes() == b"java"
    assert not (bundle / "java" / ".artifact-sha256").exists()
    assert (bundle / "ИНСТРУКЦИЯ.txt").read_text(encoding="utf-8") == "Откройте программу"
    assert zip_path == dist / "bundle" / "proverka-zapuska-0.1.0-win64.zip"
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
    assert {"Проверка_запуска/Проверка_запуска.exe", "Проверка_запуска/java/bin/java.exe",
            "Проверка_запуска/ИНСТРУКЦИЯ.txt", "Проверка_запуска/_internal/base.dll"} <= names


def test_assemble_requires_built_app(tmp_path):
    with pytest.raises(FileNotFoundError, match="сначала соберите"):
        asm.assemble("Проверка_запуска", "0.1.0", dist=tmp_path / "dist", vendor=tmp_path / "vendor")


def test_assemble_requires_jre(tmp_path):
    dist = tmp_path / "dist"
    make_tree(dist / "Проверка_запуска", {"Проверка_запуска.exe": b"exe"})
    with pytest.raises(FileNotFoundError, match="fetch_artifacts"):
        asm.assemble("Проверка_запуска", "0.1.0", dist=dist, vendor=tmp_path / "vendor")


def test_apps_registry_has_launchcheck():
    app = asm.APPS["launchcheck"]
    assert app["folder"] == "Проверка_запуска"
    assert app["zip"] == "proverka-zapuska"
    assert app["instruction"].exists()
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/python -m pytest tests/sborka/test_assemble.py -q`
Expected: `ModuleNotFoundError: No module named 'sborka.assemble'`.

- [ ] **Step 3: Написать инструкцию, точку входа, спецификацию и сборку папки**

`sborka/ИНСТРУКЦИЯ-проверка-запуска.txt`:
```
ПРОВЕРКА ЗАПУСКА КОРРЕКТОРА

Это пробная программа. Она ничего не устанавливает и ничего не меняет на компьютере —
только проверяет, запускается ли такая программа на вашем рабочем месте.

1. Скопируйте всю папку «Проверка_запуска» на флешку или на рабочий стол.
2. Откройте папку и дважды щёлкните файл «Проверка_запуска.exe».
   Первый запуск с флешки может занять до минуты — подождите.
3. Если Windows пишет «Система Windows защитила ваш компьютер», нажмите
   «Подробнее», затем «Выполнить в любом случае».
4. Появится окно с отчётом. Файл «отчёт_запуска.txt» уже сохранён рядом с программой
   (если туда нельзя записывать — на рабочем столе).
5. Пришлите автору файл «отчёт_запуска.txt» или нажмите «Скопировать» и вставьте
   текст в сообщение.

Если окно не появилось, напишите, что именно произошло: текст сообщения системы
и через сколько секунд после щелчка оно появилось.
```

`sborka/entry_launchcheck.py`:
```python
"""Точка входа для PyInstaller: абсолютный импорт, чтобы пакет собирался целиком."""

import sys

from launchcheck.app import main

sys.exit(main())
```

`sborka/launchcheck.spec`:
```python
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
```

`sborka/assemble.py`:
```python
"""Собирает папку поставки из результата PyInstaller и JRE, кладёт инструкцию и упаковывает в zip."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import launchcheck  # noqa: E402 — версия приложения

APPS = {
    "launchcheck": {
        "folder": "Проверка_запуска",
        "zip": "proverka-zapuska",
        "version": launchcheck.__version__,
        "instruction": ROOT / "sborka" / "ИНСТРУКЦИЯ-проверка-запуска.txt",
    },
}


def assemble(
    app_name: str,
    version: str,
    dist: Path = ROOT / "dist",
    vendor: Path = ROOT / "vendor",
    jre: str = "jre-windows-x64",
    instruction: Path | None = None,
    zip_name: str | None = None,
) -> Path:
    source = dist / app_name
    if not source.is_dir():
        raise FileNotFoundError(f"нет папки {source}: сначала соберите программу PyInstaller")
    jre_dir = vendor / jre
    if not jre_dir.is_dir():
        raise FileNotFoundError(f"нет папки {jre_dir}: сначала выполните python sborka/fetch_artifacts.py {jre}")

    bundle_root = dist / "bundle"
    bundle = bundle_root / app_name
    if bundle.exists():
        shutil.rmtree(bundle)
    shutil.copytree(source, bundle)
    shutil.copytree(jre_dir, bundle / "java", ignore=shutil.ignore_patterns(".artifact-sha256"))
    if instruction is not None:
        shutil.copy(instruction, bundle / "ИНСТРУКЦИЯ.txt")

    zip_path = bundle_root / (zip_name or f"{app_name}-{version}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(bundle.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(bundle_root).as_posix())
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать папку поставки и архив")
    parser.add_argument("app", choices=sorted(APPS))
    parser.add_argument("--jre", default="jre-windows-x64", help="имя JRE из artifacts.lock")
    args = parser.parse_args(argv)
    app = APPS[args.app]
    suffix = "win64" if args.jre.startswith("jre-windows") else "mac"
    zip_path = assemble(
        app["folder"],
        app["version"],
        jre=args.jre,
        instruction=app["instruction"],
        zip_name=f"{app['zip']}-{app['version']}-{suffix}.zip",
    )
    print(zip_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Тесты, затем настоящая сборка на Mac и запуск собранной программы**

Run: `.venv/bin/python -m pytest -q` — все проходят.

Run:
```bash
.venv/bin/pyinstaller --noconfirm sborka/launchcheck.spec
.venv/bin/python sborka/assemble.py launchcheck --jre jre-mac-aarch64
"dist/bundle/Проверка_запуска/Проверка_запуска" --report-only --out /tmp; echo "код $?"
cat /tmp/отчёт_запуска.txt
```
Expected: сборка без ошибок; `dist/bundle/proverka-zapuska-0.1.0-mac.zip` создан; отчёт содержит `Папка программы: …/dist/bundle/Проверка_запуска`, `Qt: 6.11.2`, `Java: OK — openjdk version "21.0.12.1"` (Java найдена по умолчанию в `java/bin/java` рядом с программой), `код 0`.

Если PyInstaller споткнётся о кириллическое имя — заменить `name="Проверка_запуска"` на `name="launchcheck"` в спецификации и `"folder": "launchcheck"` в реестре, записать это в README.

- [ ] **Step 5: Commit**

```bash
git add sborka tests/sborka/test_assemble.py && git commit -m "Поставка: спецификация PyInstaller, сборка папки с Java и инструкцией, архив"
```

---

### Task 8: Сборщик GitHub, репозиторий, первый релиз

**Files:**
- Create: `.github/workflows/windows.yml`, `docs/acceptance-stage0.md`
- Modify: `README.md` (раздел «Где взять архив»)

**Interfaces:**
- Consumes: всё из задач 1–7.
- Produces: закрытый репозиторий `aslantuk-bit/corrector`; при пуше в `main` — артефакт `proverka-zapuska-win64` с архивом; при тэге `v0.1.0` — релиз с тем же архивом.

- [ ] **Step 1: Написать workflow и лист приёмки**

`.github/workflows/windows.yml`:
```yaml
name: windows

on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    env:
      PYTHONUTF8: "1"
      QT_QPA_PLATFORM: offscreen
    steps:
      - uses: actions/checkout@v7

      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"

      - name: Зависимости
        run: pip install -r requirements-dev.txt

      - name: Тесты
        run: python -m pytest -q

      - name: Java по замку
        run: python sborka/fetch_artifacts.py jre-windows-x64

      - name: PyInstaller
        run: pyinstaller --noconfirm sborka/launchcheck.spec

      - name: Папка поставки и архив
        run: python sborka/assemble.py launchcheck

      - name: Запуск собранной программы без окна
        shell: pwsh
        run: |
          $exe = Resolve-Path "dist/bundle/Проверка_запуска/Проверка_запуска.exe"
          $out = Join-Path $env:RUNNER_TEMP "report"
          New-Item -ItemType Directory -Force $out | Out-Null
          $p = Start-Process -FilePath $exe -ArgumentList "--report-only","--out","`"$out`"" -Wait -PassThru
          $report = Join-Path $out "отчёт_запуска.txt"
          Get-Content $report
          if ($p.ExitCode -ne 0) { throw "код возврата $($p.ExitCode)" }
          if (-not (Select-String -Path $report -Pattern "Java: OK" -Quiet)) { throw "в отчёте нет строки 'Java: OK'" }
          if (-not (Select-String -Path $report -Pattern "Qt: 6.11.2" -Quiet)) { throw "в отчёте нет строки 'Qt: 6.11.2'" }

      - uses: actions/upload-artifact@v7
        with:
          name: proverka-zapuska-win64
          path: dist/bundle/*.zip

      - uses: softprops/action-gh-release@v3
        if: startsWith(github.ref, 'refs/tags/v')
        with:
          files: dist/bundle/*.zip
```

`docs/acceptance-stage0.md`:
```markdown
# Приёмка этапа 0: «Проверка запуска» на рабочем ПК

Что взять: архив `proverka-zapuska-0.1.0-win64.zip` из релиза v0.1.0 на GitHub, распаковать,
папку «Проверка_запуска» записать на флешку.

На рабочем ПК (без прав администратора, без интернета):

1. Открыть папку с флешки, дважды щёлкнуть «Проверка_запуска.exe». Засечь время до окна.
2. Если появилось предупреждение SmartScreen — «Подробнее» → «Выполнить в любом случае».
   Если кнопки «Выполнить в любом случае» нет — записать точный текст окна: это запрет политики.
3. В окне должно быть «Всё запустилось». Нажать «Скопировать», вставить в сообщение автору,
   либо прислать файл «отчёт_запуска.txt» (рядом с программой или на рабочем столе).
4. Повторить пункт 1, скопировав папку на рабочий стол: сравнить время запуска.

Что считается успехом: окно открылось, в отчёте «Qt: 6.11.2», «Java: OK», «ИТОГ: всё работает».
Что считается провалом и что делать дальше:
- окно не открылось, сообщение о запрете политики — переносные программы на этих ПК запрещены,
  нужно согласовывать с администраторами;
- «Java: ОШИБКА» — переносная Java не запускается, для русского остаётся запасная орфография без
  LanguageTool (спецификация, раздел 5.2), решение о дальнейшем пути принимает автор;
- запуск с флешки дольше минуты — в инструкции к Корректору советовать копирование на рабочий стол.
```

Добавить в `README.md`:
```markdown
## Где взять архив

GitHub → репозиторий `aslantuk-bit/corrector` → «Releases» → `proverka-zapuska-<версия>-win64.zip`.
Между релизами свежий архив лежит в артефактах последнего запуска на вкладке «Actions».
Лист приёмки на рабочем ПК: `docs/acceptance-stage0.md`.
```

- [ ] **Step 2: Создать закрытый репозиторий через API (как в llm-calc) и запушить**

```bash
cd ~/corrector
TOKEN=$(printf 'protocol=https\nhost=github.com\n\n' | git credential-osxkeychain get | sed -n 's/^password=//p')
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d '{"name":"corrector","private":true,"description":"Корректор: проверка орфографии, пунктуации и стиля юридических текстов (ru/kk) с флешки"}'
git add -A && git commit -m "Сборщик GitHub для Windows, лист приёмки этапа 0"
git remote add origin https://github.com/aslantuk-bit/corrector.git
git push -u origin main
```
Expected: `201`; пуш прошёл; в GitHub на вкладке «Actions» запустился workflow `windows`.

- [ ] **Step 3: Дождаться сборки и проверить артефакт**

```bash
TOKEN=$(printf 'protocol=https\nhost=github.com\n\n' | git credential-osxkeychain get | sed -n 's/^password=//p')
curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/aslantuk-bit/corrector/actions/runs?per_page=1" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['status'], r['conclusion'], r['html_url'])"
```
Повторять раз в минуту до `completed success`. При провале открыть журнал шага по ссылке, починить, закоммитить, запушить снова. Обычные причины: кириллическое имя exe (откат на `launchcheck`), отсутствие `Qt: …` из-за неполного сбора PySide6 (добавить `hiddenimports=["PySide6.QtWidgets"]`), SmartScreen на сборщике не мешает.

Скачать артефакт и посмотреть состав:
```bash
RUN=$(curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/aslantuk-bit/corrector/actions/runs?per_page=1" | python3 -c "import sys,json; print(json.load(sys.stdin)['workflow_runs'][0]['id'])")
curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/aslantuk-bit/corrector/actions/runs/$RUN/artifacts" | python3 -c "import sys,json; [print(a['name'], a['size_in_bytes']//1000000, 'МБ', a['archive_download_url']) for a in json.load(sys.stdin)['artifacts']]"
```
Expected: один артефакт `proverka-zapuska-win64`, размер порядка 60–120 МБ.

- [ ] **Step 4: Тэг и релиз**

```bash
git tag -a v0.1.0 -m "Проверка запуска 0.1.0" && git push origin v0.1.0
```
Дождаться второго запуска workflow (по тэгу); проверить, что в «Releases» появился `v0.1.0` с `proverka-zapuska-0.1.0-win64.zip`:
```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/repos/aslantuk-bit/corrector/releases/latest | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['tag_name'], [(a['name'], a['size']//1000000) for a in r['assets']])"
```

---

### Task 9: Виртуальная Windows на Mac и передача пользователю

**Files:**
- Create: `docs/vm-setup.md`

**Interfaces:**
- Consumes: архив релиза из задачи 8.
- Produces: установленные UTM и CrystalFetch; пошаговая инструкция для ручной части (установку Windows автор делает сам, это интерактивно).

- [ ] **Step 1: Поставить UTM и CrystalFetch**

Run: `brew install --cask utm crystalfetch`
Expected: обе программы в `/Applications`.

- [ ] **Step 2: Написать инструкцию по виртуальной машине**

`docs/vm-setup.md`:
```markdown
# Виртуальная Windows 11 ARM на Mac (UTM)

Нужна один раз, чтобы смотреть собранные программы глазами до передачи коллегам.
Сборка для Windows x64 в Windows 11 ARM работает через встроенную эмуляцию.

1. Образ: открыть CrystalFetch → Windows 11 → архитектура ARM64, язык «Русский» →
   «Скачать» (около 5 ГБ, кладёт ISO в «Загрузки»).
2. UTM → «Создать новую виртуальную машину» → «Виртуализация» → «Windows» →
   отметить «Установить Windows 10 или выше», указать ISO → память 6 ГБ, 4 ядра,
   диск 64 ГБ → имя «Windows 11 ARM» → «Сохранить».
3. Запустить; при «Press any key to boot from CD» нажать любую клавишу. Пройти установку
   Windows: язык русский, «У меня нет ключа продукта», выпуск Pro, без учётной записи
   Microsoft (на шаге «Войдите» отключить сеть в UTM или нажать Shift+F10 и выполнить
   `oobe\bypassnro`, после перезапуска появится «У меня нет интернета»).
4. После входа установить гостевые дополнения: в UTM смонтировать образ SPICE tools
   (вкладка привода CD → «utm-guest-tools»), запустить установщик в Windows, перезапустить.
5. Общая папка: в настройках машины UTM → «Общий каталог» → выбрать `~/corrector/dist/bundle`;
   в Windows она видна как сетевой диск в проводнике.
6. Проверка сборки: скопировать папку «Проверка_запуска» из общей папки на рабочий стол
   Windows, запустить `Проверка_запуска.exe`, убедиться, что окно открылось и в отчёте
   «Java: OK». Для настоящей проверки с флешки в UTM → «USB» пробросить флешку в машину.
7. Для будущих этапов поставить в машине LibreOffice (просмотр примечаний Word):
   скачать с libreoffice.org в машине или положить установщик в общую папку.

Что делает автор руками: шаги 1–5 (интерактивная установка Windows, около часа).
```

- [ ] **Step 3: Commit**

```bash
git add docs/vm-setup.md && git commit -m "Инструкция: виртуальная Windows 11 ARM в UTM для проверки сборок" && git push
```

- [ ] **Step 4: Сообщить пользователю итог этапа 0**

В отчёте: ссылка на релиз с архивом; что проверено на сборщике (тесты, запуск собранной программы, строки `Qt` и `Java: OK` в отчёте); что осталось за пользователем — установить Windows в UTM по `docs/vm-setup.md`, отнести архив на рабочий ПК по `docs/acceptance-stage0.md` и прислать `отчёт_запуска.txt`; какие ответы из отчёта меняют дальнейший план (запрет политики, Java не запускается, медленный старт с флешки).

---

## Самопроверка плана

- Покрытие спецификации (раздел 15, этап 0): репозиторий и окружение — задача 1; JRE в `vendor/` — задача 6; каркас workflow и нулевая сборка «Проверка_запуска» — задачи 2–8 (окно PySide6 с версией Windows, памятью, признаком запуска со съёмного диска, результатом запуска Java; файл `отчёт_запуска.txt`); проверка цепочки «GitHub → архив → флешка → закрытый ПК» — задачи 8–9 плюс лист приёмки; виртуальная машина UTM — задача 9.
- Заглушек нет: у каждого шага с кодом есть код; единственная временная заглушка (`window.py` в задаче 4) заменяется в задаче 5.
- Имена согласованы: `probes.default_java`, `report.run_all/build_report/save_report/REPORT_NAME/OK_LINE/FAIL_LINE`, `app.main`, `window.ReportWindow/show`, `fetch_artifacts.fetch/load_lock/sha256_of/main`, `assemble.assemble/APPS/main` используются одинаково во всех задачах.
