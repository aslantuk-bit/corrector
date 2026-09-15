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
