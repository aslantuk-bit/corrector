"""Сверка названий органов и законов с эталонным списком."""

from __future__ import annotations

import difflib

from corrector.core.issue import Category, Issue, Level
from corrector.core.text import words
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext


def _keys(fragment: str, canonical: str) -> tuple[list[str], list[str]]:
    """Начала слов (до 4 букв, не длиннее эталонного слова): склонение не мешает сравнению."""
    frag_words, canon_words = words(fragment), words(canonical)
    frag_keys = [w.text[: min(4, len(c.text))] for w, c in zip(frag_words, canon_words)]
    canon_keys = [c.text[: min(4, len(c.text))] for c in canon_words]
    return frag_keys, canon_keys


def find_candidates(text: str, canonical: str) -> list[tuple[int, int]]:
    """Отрезки текста той же длины в словах, что эталон, с теми же первым и последним словами (по началам слов)."""
    canon_words = words(canonical)
    text_words = words(text)
    n = len(canon_words)
    if n < 2:
        return []
    result = []
    first, last = canon_words[0].text[:4].lower(), canon_words[-1].text[:4].lower()
    for i in range(len(text_words) - n + 1):
        window = text_words[i:i + n]
        if window[0].text[:4].lower() == first and window[-1].text[:4].lower() == last:
            result.append((window[0].start, window[-1].end))
    return result


def similar(fragment: str, canonical: str) -> bool:
    return difflib.SequenceMatcher(None, fragment.lower(), canonical.lower()).ratio() >= 0.85


def word_diff(fragment: str, canonical: str) -> tuple[int, float]:
    """Сколько слов отличается (без учёта регистра и склонения) и сходство самого отличающегося слова."""
    frag_keys, canon_keys = _keys(fragment, canonical)
    differing = [(f, c) for f, c in zip(frag_keys, canon_keys) if f.lower() != c.lower()]
    if not differing:
        return 0, 1.0
    frag_words, canon_words = words(fragment), words(canonical)
    worst = 1.0
    for f, c in zip(frag_words, canon_words):
        if f.text[:4].lower() != c.text[:4].lower():
            worst = min(worst, difflib.SequenceMatcher(None, f.text.lower(), c.text.lower()).ratio())
    return len(differing), worst


class OfficialNamesRule(Rule):
    id, lang, category, level = "names.official", "any", Category.STYLE, Level.HINT
    message = "Название отличается от официального"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        canon_list = doc.resources.official_kk if para.lang == "kk" else doc.resources.official_ru
        issues, taken = [], []
        for canonical in canon_list:
            for start, end in find_candidates(para.text, canonical):
                if any(s <= start < e for s, e in taken):
                    continue
                fragment = para.text[start:end]
                frag_keys, canon_keys = _keys(fragment, canonical)
                if frag_keys == canon_keys:
                    continue  # совпадает или лишь склоняется
                differing, worst = word_diff(fragment, canonical)
                if differing == 0:
                    issues.append(make_issue(self, para, start, end, [canonical], f"Регистр букв: официально «{canonical}»"))
                    taken.append((start, end))
                elif differing == 1 and worst >= 0.75:
                    issues.append(make_issue(self, para, start, end, [canonical], f"Официальное название: «{canonical}»"))
                    taken.append((start, end))
        return issues
