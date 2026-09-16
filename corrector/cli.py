"""Командная строка: проверить файл или папку, напечатать итог, записать отчёт или JSON."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from corrector import __version__
from corrector.core import log as log_setup
from corrector.core import paths
from corrector.core.issue import CATEGORY_TITLES, LEVEL_TITLES, Issue, Level
from corrector.core.settings import FILE_NAME as SETTINGS_FILE
from corrector.core.settings import Settings
from corrector.core.userdict import FILE_NAME as DICT_FILE
from corrector.core.userdict import UserDictionary
from corrector.docx_io import model
from corrector.engines import factory, pipeline
from corrector.engines.base import EngineStatus


def report_path(docx_path: Path, out_dir: Path | None) -> Path:
    folder = out_dir or docx_path.parent
    return folder / f"{docx_path.stem}_отчёт.txt"


def counts(issues: list[Issue]) -> dict[Level, int]:
    return {level: sum(1 for i in issues if i.level is level) for level in Level}


def summary_line(name: str, issues: list[Issue]) -> str:
    c = counts(issues)
    return f"{name}: {len(issues)} замечаний (ошибок {c[Level.ERROR]}, предупреждений {c[Level.WARNING]}, подсказок {c[Level.HINT]})"


def format_report(doc: model.DocumentModel, issues: list[Issue], statuses: list[EngineStatus]) -> str:
    engines = "; ".join(
        f"{s.name} — {'работает' if s.available else 'недоступен'}" + (f" ({s.note})" if s.note else "") for s in statuses
    )
    lines = [
        f"Корректор {__version__}, отчёт о проверке",
        f"Файл: {doc.path}",
        f"Время: {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}",
        f"Движки: {engines}",
        summary_line(doc.path.name, issues),
        "",
    ]
    for issue in issues:
        text = doc.paragraphs[issue.paragraph].text
        fragment = text[issue.start:issue.end]
        suggestions = ", ".join(issue.suggestions)
        arrow = f" → {suggestions}" if suggestions else ""
        lines.append(
            f"абзац {issue.paragraph + 1} | {CATEGORY_TITLES[issue.category]} | {LEVEL_TITLES[issue.level]} | "
            f"«{fragment}»{arrow} | {issue.message}"
        )
    return "\n".join(lines) + "\n"


def collect_files(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.glob("*.docx") if not p.name.startswith("~$"))
    return [target]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="corrector", description="Проверка документов Word на русском и казахском")
    parser.add_argument("--check", type=Path, required=True, help="файл .docx или папка")
    parser.add_argument("--out", type=Path, help="папка для отчётов (по умолчанию рядом с файлом)")
    parser.add_argument("--report", action="store_true", help="записать текстовый отчёт <имя>_отчёт.txt")
    parser.add_argument("--json", action="store_true", help="напечатать замечания в JSON")
    parser.add_argument("--no-lt", action="store_true", help="не запускать LanguageTool (только словари)")
    parser.add_argument("--no-suggestions", action="store_true", help="не подбирать варианты замены (быстрее)")
    parser.add_argument("--lang", choices=["auto", "ru", "kk"], default=None, help="язык документа (по умолчанию из настроек)")
    parser.add_argument("--version", action="version", version=f"Корректор {__version__}")
    args = parser.parse_args(argv)

    user_dir = paths.user_dir()
    log_setup.setup_logging(user_dir)
    settings = Settings.load(user_dir / SETTINGS_FILE)
    if args.lang:
        settings.language = args.lang
    user_dict = UserDictionary(user_dir / DICT_FILE)
    engines = factory.build_engines(user_dict, no_lt=args.no_lt, user_dir=user_dir, suggestions=not args.no_suggestions)
    if engines.rule_resources is not None:
        for error in engines.rule_resources.user_rule_errors:
            print(f"правила.yaml: {error}", file=sys.stderr)
    failed = False
    all_json: list[dict] = []
    try:
        for path in collect_files(args.check):
            try:
                doc = model.load(path)
            except model.DocxError as error:
                print(f"{path.name}: {error}", file=sys.stderr)
                failed = True
                continue
            issues = pipeline.check_document(doc, engines, user_dict, settings)
            if args.json:
                for issue in issues:
                    data = issue.to_dict()
                    data["file"] = str(path)
                    data["fragment"] = doc.paragraphs[issue.paragraph].text[issue.start:issue.end]
                    all_json.append(data)
            else:
                print(summary_line(path.name, issues))
            if args.report:
                target = report_path(path, args.out)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(format_report(doc, issues, engines.statuses()), encoding="utf-8-sig")
    finally:
        engines.close()
    if args.json:
        print(json.dumps(all_json, ensure_ascii=False, indent=1))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
