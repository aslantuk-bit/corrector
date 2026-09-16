"""Словарный движок: неизвестные слова абзаца с учётом лексикона, словаря пользователя и второго языка."""

from __future__ import annotations

import re
from pathlib import Path

from collections import Counter

from corrector.core.issue import Category, Issue, Level
from corrector.core.text import Token, sentences, words
from corrector.core.userdict import UserDictionary
from corrector.engines.base import EngineStatus
from corrector.engines.hunspell import SpellDictionary

LATIN = re.compile(r"[A-Za-z]")
UNKNOWN_MESSAGE = "Возможно, орфографическая ошибка"
NAME_MESSAGE = "Незнакомое слово с заглавной буквы: имя или название? Проверьте написание"


def load_lexicon(path: Path) -> set[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return set()
    return {line.strip().lower() for line in lines if line.strip() and not line.lstrip().startswith("#")}


def load_names(path: Path) -> set[str]:
    """Имена и названия из корпуса: регистр важен."""
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return set()
    return {line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")}


def inside_quotes(text: str, position: int) -> bool:
    before = text[:position]
    if before.count("«") > before.count("»"):
        return True
    return before.count('"') % 2 == 1


def looks_like_abbreviation(word: str) -> bool:
    """ГПК, АППК, АҚБтК: почти сплошь заглавные, коротко."""
    upper = sum(ch.isupper() for ch in word)
    lower = sum(ch.islower() for ch in word)
    return upper >= 2 and lower <= 1 and len(word) <= 7


class SpellEngine:
    def __init__(
        self,
        name: str,
        dictionary: SpellDictionary,
        lexicon: set[str],
        user_dict: UserDictionary,
        other: SpellDictionary | None = None,
        foreign_message: str = "",
        suggestions: bool = True,
        names: set[str] | None = None,
    ) -> None:
        self.suggestions = suggestions
        self.names = names or set()
        self.name = name
        self.dictionary = dictionary
        self.lexicon = lexicon
        self.user_dict = user_dict
        self.other = other
        self.foreign_message = foreign_message

    def status(self) -> EngineStatus:
        return EngineStatus(self.name, True)

    def check(self, paragraphs: list[tuple[int, str]]) -> list[Issue]:
        counts = Counter(t.text for _, text in paragraphs for t in words(text))
        issues: list[Issue] = []
        for index, text in paragraphs:
            issues += self.check_tokens(index, text, words(text), counts=counts)
        return issues

    def check_tokens(self, index: int, text: str, tokens: list[Token], foreign_hints: bool = True,
                     counts: Counter | None = None) -> list[Issue]:
        issues: list[Issue] = []
        starts = {s for s, _ in sentences(text)}
        for token in tokens:
            word = token.text
            if self._skip(word) or self._accepted(word):
                continue
            if self.user_dict.covers(text, token.start, token.end):
                continue
            if self.other is not None and self.other.known(word):
                if foreign_hints and not inside_quotes(text, token.start):
                    issues.append(Issue(index, token.start, token.end, Category.STYLE, Level.HINT,
                                        f"{self.name}:foreign", self.name, self.foreign_message))
                continue
            if word[0].isupper() and word[1:].islower() and token.start not in starts:
                if counts is not None and counts[word] >= 2:
                    continue  # имя, написанное одинаково не один раз
                issues.append(Issue(index, token.start, token.end, Category.SPELLING, Level.HINT,
                                    f"{self.name}:name", self.name, NAME_MESSAGE))
                continue
            variants = self.dictionary.suggest(word) if self.suggestions else []
            issues.append(Issue(index, token.start, token.end, Category.SPELLING, Level.ERROR,
                                f"{self.name}:unknown", self.name, UNKNOWN_MESSAGE, variants))
        return issues

    def accepts(self, word: str) -> bool:
        """Слово не считается ошибкой: пропускаемое, известное словарю, лексикону, списку имён или словарю пользователя."""
        return self._skip(word) or self._accepted(word)

    def _skip(self, word: str) -> bool:
        if len(word) < 2 or any(ch.isdigit() for ch in word):
            return True
        if looks_like_abbreviation(word):
            return True
        return bool(LATIN.search(word))

    def _accepted(self, word: str) -> bool:
        if word in self.names:
            return True
        lowered = word.lower()
        if lowered in self.lexicon or self.user_dict.contains(word) or self.dictionary.known(word):
            return True
        parts = [p for p in re.split(r"[-'’]", word) if p]
        return len(parts) > 1 and all(p.lower() in self.lexicon or self.dictionary.known(p) for p in parts)
