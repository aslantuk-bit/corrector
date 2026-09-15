"""Сбор проб в один словарь и текст отчёта, который пользователь пришлёт автору."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from launchcheck import __version__, probes

REPORT_NAME = "отчёт_запуска.txt"
OK_LINE = "ИТОГ: всё работает"
FAIL_LINE = "ИТОГ: Java не запустилась — пришлите этот отчёт автору"


def check_java(java_exe: Path) -> dict[str, object]:
    """Прямой запуск java; при отказе — копия в папку без символов вне кодовой страницы и повторный запуск."""
    direct_ok, direct_text = probes.java_version(java_exe)
    result: dict[str, object] = {
        "java_прямо_ok": direct_ok,
        "java_прямо": direct_text,
        "java_копия": "",
        "java_ok": direct_ok,
        "java": direct_text,
        "java_путь": str(java_exe),
    }
    if direct_ok:
        return result
    copy_dir, note = probes.copy_java_to_safe_dir(java_exe.parent.parent, encoding=probes.active_code_page())
    result["java_копия"] = note
    if copy_dir is not None:
        copy_exe = copy_dir / "bin" / java_exe.name
        copy_ok, copy_text = probes.java_version(copy_exe)
        result.update({"java_ok": copy_ok, "java": copy_text, "java_путь": str(copy_exe)})
    return result


def run_all(base_dir: Path, java_exe: Path | None = None) -> dict[str, object]:
    java_exe = java_exe or probes.default_java(base_dir)
    results: dict[str, object] = {
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
        "кодовая_страница": probes.active_code_page(),
    }
    results.update(check_java(java_exe))
    return results


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
        f"Кодовая страница: {r['кодовая_страница'] or 'не Windows'}",
    ]
    if r["java_копия"]:
        lines.append(f"Java напрямую: ОШИБКА — {r['java_прямо']}")
        lines.append(f"Копия Java: {r['java_копия']}")
    lines += [
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
