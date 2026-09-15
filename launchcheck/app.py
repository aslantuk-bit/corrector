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
