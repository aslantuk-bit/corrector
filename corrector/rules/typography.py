"""Типографика, общая для обоих языков."""

from __future__ import annotations

from corrector.core.issue import Category, Level
from corrector.rules.patterns import PatternRule

W, T = Level.WARNING, Category.TYPOGRAPHY
CYR = "А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі"
UP = "А-ЯЁӘҒҚҢӨҰҮҺІ"
# однобуквенные сокращения только строчными: заглавная «Г.» перед заглавной — это инициал
ABBREVIATIONS = r"(?:[Сс]т|[Сс]тр|[Пп]п|п|ч|[Аа]бз|[Гг]л|[Рр]азд|г|[Уу]л|д|[Кк]в|[Кк]аб|[Оо]ф|т|[Бб]ап|[Тт]арм|б|қ|[Кк]өш)"


def _rule(id, message, pattern, replacement=None, flags=0, condition=None, lang="any"):
    return PatternRule(id, lang, T, W, message, pattern, replacement, flags, condition)


TYPOGRAPHY_RULES = [
    _rule("typo.double_space", "Двойной пробел", r"(?<=\S) {2,}(?=\S)", " "),
    _rule("typo.space_before_punct", "Пробел перед знаком препинания", r"(?<=\S) +(?=[,;:!?])", ""),
    _rule("typo.space_before_punct", "Пробел перед точкой", r"(?<=[^\s\d.]) +(?=\.(?:\s|$))", ""),
    _rule("typo.no_space_after_punct", "Нет пробела после знака препинания", rf"(?<=[{CYR}»)])([,;])(?=[{CYR}«(])", r"\1 "),
    _rule("typo.quotes", "Кавычки-лапки: в документах приняты «ёлочки»", r'"([^"\n]{1,120})"', r"«\1»"),
    _rule("typo.dash", "Между пробелами ставится тире, а не дефис", r"(?<=\S) - (?=\S)", " — "),
    _rule("typo.abbrev_space", "Нет пробела после сокращения", rf"\b({ABBREVIATIONS})\.(?=[\d{UP}])", r"\1. "),
    _rule("typo.abbrev_space", "Нет пробела после знака номера", r"№(?=\d)", "№ "),
    _rule("typo.year_g", "Год и «г.» разделяются пробелом", r"(?<=\d{4})г\.", " г."),
    _rule("typo.initials", "Инициалы разделяются пробелом", rf"(?<=\b[{UP}]\.)([{UP}]\.)(?!\S)", r" \1"),
]
