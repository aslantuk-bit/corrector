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
