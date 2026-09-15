"""Смешанные алфавиты: латиница внутри кириллического слова и римские цифры кириллицей."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext

LATIN = re.compile(r"[A-Za-z]")
CYRILLIC = re.compile(r"[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]")
LOOKALIKES = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "i": "і",
              "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О", "P": "Р", "T": "Т", "X": "Х", "I": "І"}
ROMAN_CYRILLIC = re.compile(r"(?<![\wА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі])[ІХV]{1,5}(?![\wА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі])")
ROMAN_MAP = {"І": "I", "Х": "X", "V": "V"}


def is_mixed(word: str) -> bool:
    return bool(LATIN.search(word)) and bool(CYRILLIC.search(word))


def fix_lookalikes(word: str) -> str | None:
    fixed = []
    for ch in word:
        if LATIN.match(ch):
            if ch not in LOOKALIKES:
                return None
            fixed.append(LOOKALIKES[ch])
        else:
            fixed.append(ch)
    return "".join(fixed)


class MixedAlphabetRule(Rule):
    id, lang, category, level = "alpha.mixed", "any", Category.SPELLING, Level.ERROR
    message = "В слове смешаны латинские и кириллические буквы"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for token in para.words:
            if is_mixed(token.text):
                fixed = fix_lookalikes(token.text)
                issues.append(make_issue(self, para, token.start, token.end, [fixed] if fixed else []))
        return issues


class RomanNumeralRule(Rule):
    id, lang, category, level = "alpha.roman", "any", Category.TYPOGRAPHY, Level.WARNING
    message = "Римская цифра набрана кириллическими буквами: используйте латинские I, V, X"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for match in ROMAN_CYRILLIC.finditer(para.text):
            text = match.group()
            if "І" not in text and "Х" not in text:
                continue
            if len(text) == 1 and para.lang == "kk":
                continue
            issues.append(make_issue(self, para, match.start(), match.end(), ["".join(ROMAN_MAP[c] for c in text)]))
        return issues
