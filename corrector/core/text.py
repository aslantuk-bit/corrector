"""Токены и предложения для обоих языков."""

from __future__ import annotations

import re
from dataclasses import dataclass

LETTERS = "A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі"
UPPER = "A-ZА-ЯЁӘҒҚҢӨҰҮҺІ"
TOKEN_RE = re.compile(
    rf"(?P<number>\d+(?:[.,]\d+)*(?:-(?:\d+|[{LETTERS}]+))*)"
    rf"|(?P<word>[{LETTERS}]+(?:[-'’][{LETTERS}]+)*)"
    rf"|(?P<space>\s+)"
    rf"|(?P<punct>[^\s{LETTERS}\d])"
)
ABBREVIATIONS = {
    "ru": {
        "ст", "ч", "п", "пп", "абз", "гл", "разд", "г", "гг", "ул", "пр", "д", "кв", "к", "стр", "тыс", "млн", "млрд",
        "руб", "тг", "тнг", "коп", "им", "т", "е", "см", "ср", "обл", "с", "пос", "оф", "каб", "зд", "мкр", "р", "н",
        "т.е", "т.д", "т.п", "т.к", "и.о", "уч", "инв", "экз", "лтд", "мм", "га", "кв.м", "чел", "ред",
    },
    "kk": {"т.б", "т.с.с", "ж", "қ", "к", "көш", "ауд", "обл", "млн", "млрд", "мың", "га", "тг", "б", "бет", "тарм", "ш", "м", "а", "мкр"},
}
END_RE = re.compile(r"[.!?…]+[»\")\]]*")


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str
    kind: str  # word | number | punct | space


def tokenize(text: str) -> list[Token]:
    return [Token(m.start(), m.end(), m.group(), m.lastgroup) for m in TOKEN_RE.finditer(text)]


def words(text: str) -> list[Token]:
    return [t for t in tokenize(text) if t.kind == "word"]


def sentences(text: str, lang: str = "ru") -> list[tuple[int, int]]:
    abbreviations = ABBREVIATIONS.get(lang, set()) | ABBREVIATIONS["ru"]
    spans: list[tuple[int, int]] = []
    start = _skip_space(text, 0)
    for match in END_RE.finditer(text):
        end = match.end()
        if end < start:
            continue
        if not _is_sentence_end(text, match.start(), end, abbreviations):
            continue
        spans.append((start, end))
        start = _skip_space(text, end)
    if start < len(text) and text[start:].strip():
        spans.append((start, len(text.rstrip())))
    return spans


def _skip_space(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def _is_sentence_end(text: str, mark_start: int, end: int, abbreviations: set[str]) -> bool:
    after = _skip_space(text, end)
    if after >= len(text):
        return True
    if after == end:  # знак прилип к следующему символу: «т.е.» или число «5.1»
        return False
    if not (text[after].isupper() or text[after].isdigit() or text[after] in "«\"("):
        return False
    if text[mark_start] != ".":
        return True
    before = text[:mark_start]
    word = re.search(rf"([{LETTERS}][{LETTERS}.]*)$", before)
    if word:
        token = word.group(1).lower().rstrip(".")
        if token in abbreviations or (len(token) == 1 and word.group(1)[0].isupper()):
            return False
    number = re.search(r"(?:^|\n)\s*\d+$", before)
    if number:  # «1.» в начале абзаца или строки — номер пункта
        return False
    return True
