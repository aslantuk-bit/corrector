"""Стеммер казахского (kazsearch): основа слова для правил повторов и терминов."""

from __future__ import annotations

from pathlib import Path

from kazsearch import Lexicon, StemConfig
from kazsearch import stem as _stem

from corrector.core import paths
from corrector.core.text import Token, words


class KazakhStemmer:
    def __init__(self, dict_path: Path) -> None:
        self.config = StemConfig(lexicon=Lexicon.load(str(dict_path)))

    def stem(self, word: str) -> str:
        return _stem(word.lower(), self.config)

    def stems(self, text: str) -> list[tuple[Token, str]]:
        return [(token, self.stem(token.text)) for token in words(text)]


def default() -> KazakhStemmer:
    return KazakhStemmer(paths.data_dir() / "kk" / "kaz_stems.dict")
