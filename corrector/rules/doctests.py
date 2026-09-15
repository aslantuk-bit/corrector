"""Таблицы примеров из docs/rules-*.md как тестовые случаи."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADER_RE = re.compile(r"^## (?P<id>[a-z_]+\.[a-z0-9_]+) — ")
META_RE = re.compile(r"Язык: (?P<lang>ru|kk|any)")


@dataclass(frozen=True)
class DocCase:
    rule_id: str
    lang: str
    wrong: str
    right: str
    line: int


def parse_rule_docs(path: Path) -> list[DocCase]:
    cases: list[DocCase] = []
    rule_id, lang = None, "ru"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return cases
    for number, line in enumerate(lines, 1):
        header = HEADER_RE.match(line)
        if header:
            rule_id, lang = header.group("id"), "ru"
            continue
        meta = META_RE.search(line)
        if meta and rule_id:
            lang = meta.group("lang")
            continue
        if rule_id and line.startswith("|") and not line.startswith("|---") and "Неправильно" not in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0]:
                case_lang = "ru" if lang == "any" else lang
                cases.append(DocCase(rule_id, case_lang, cells[0], cells[1], number))
    return cases
