"""Прогон конвейера по выборке и отчёт о шуме правил."""

from __future__ import annotations

import argparse
import collections
import json
import time
from pathlib import Path

from corrector.core.settings import Settings
from corrector.core.userdict import UserDictionary
from corrector.docx_io import model
from corrector.engines import factory, pipeline


def run(sample: Path, no_lt: bool, suggestions: bool) -> tuple[dict[str, list[dict]], dict[str, list[str]], float]:
    started = time.time()
    user_dict = UserDictionary(sample / "словарь-пустой.txt")
    engines = factory.build_engines(user_dict, no_lt=no_lt, suggestions=suggestions, user_dir=sample)
    issues_by_lang: dict[str, list[dict]] = {}
    files_by_lang: dict[str, list[str]] = {}
    try:
        for lang in ("ru", "kk"):
            folder = sample / lang
            files_by_lang[lang] = sorted(p.name for p in folder.glob("*.docx")) if folder.is_dir() else []
            issues_by_lang[lang] = []
            for name in files_by_lang[lang]:
                doc = model.load(folder / name)
                for issue in pipeline.check_document(doc, engines, user_dict, Settings()):
                    data = issue.to_dict()
                    data["file"] = name
                    data["fragment"] = doc.paragraphs[issue.paragraph].text[issue.start:issue.end]
                    issues_by_lang[lang].append(data)
    finally:
        engines.close()
    return issues_by_lang, files_by_lang, time.time() - started


def format_report(issues: list[dict], files: list[str], lang: str, seconds: float) -> str:
    total = len(files) or 1
    by_rule = collections.Counter(f"{i['engine']}:{i['rule_id']}" for i in issues)
    docs = collections.defaultdict(set)
    examples = collections.defaultdict(list)
    for i in issues:
        key = f"{i['engine']}:{i['rule_id']}"
        docs[key].add(i["file"])
        shown = [e.split(" → ")[0] for e in examples[key]]
        if len(examples[key]) < 3 and i["fragment"] not in shown:
            examples[key].append(f"{i['fragment']} → {', '.join(i['suggestions'][:2]) or '—'}")
    lines = [f"### {lang}: {len(issues)} замечаний в {len(files)} актах, {len(issues)/total:.1f} на акт, {seconds:.0f} с", "",
             "| Правило | Замечаний | Актов | Примеры |", "|---|---|---|---|"]
    for key, count in by_rule.most_common():
        share = len(docs[key]) / total
        flag = " ⚠ разобрать" if share > 0.34 else ""
        lines.append(f"| {key} | {count} | {len(docs[key])}/{len(files)} ({share * 100:.0f} %){flag} | {'; '.join(examples[key]).replace('|', '¦')} |")
    spelling = [i for i in issues if i["category"] == "spelling"]
    capitalized = sum(1 for i in spelling if i["fragment"][:1].isupper())
    frag = collections.Counter(i["fragment"] for i in spelling)
    lines += ["", f"Орфография: {len(spelling)} замечаний, с заглавной буквы: {capitalized} из {len(spelling)}.",
              "Частые фрагменты: " + ", ".join(f"{w} ({n})" for w, n in frag.most_common(40)), ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=Path("vendor/corpus-sample"))
    parser.add_argument("--out", type=Path, default=Path("docs/corpus-report.md"))
    parser.add_argument("--no-lt", action="store_true")
    parser.add_argument("--no-suggestions", action="store_true")
    args = parser.parse_args(argv)
    issues, files, seconds = run(args.sample, args.no_lt, not args.no_suggestions)
    (args.sample / "issues.json").write_text(json.dumps(issues, ensure_ascii=False, indent=1), encoding="utf-8")
    report = ("# Отчёт о шуме правил по выборке корпуса\n\nВыборка: `tools/corpus_sample.py`, прогон: `tools/corpus_run.py`. "
              "Правило с долей актов выше трети помечено «⚠ разобрать».\n\n")
    report += "".join(format_report(issues[lang], files[lang], lang, seconds) for lang in ("ru", "kk"))
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
