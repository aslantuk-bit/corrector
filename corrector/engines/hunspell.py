"""Словарь Hunspell через spylls: проверка слова и варианты замены с кэшем."""

from __future__ import annotations

from itertools import islice
from pathlib import Path

from spylls.hunspell import Dictionary


class SpellDictionary:
    def __init__(self, base: Path) -> None:
        self.base = Path(base)
        self.dictionary = Dictionary.from_files(str(self.base))
        self._suggestions: dict[str, list[str]] = {}

    def known(self, word: str) -> bool:
        return bool(self.dictionary.lookup(word))

    def suggest(self, word: str, limit: int = 5) -> list[str]:
        if word not in self._suggestions:
            self._suggestions[word] = list(islice(self.dictionary.suggest(word), limit))
        return self._suggestions[word]
