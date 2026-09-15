"""Словарь исключений пользователя: слова и фразы по одной на строку, регистр не важен, «#» — комментарий."""

from __future__ import annotations

from pathlib import Path

FILE_NAME = "словарь.txt"
HEADER = "# Словарь исключений Корректора: одно слово или фраза на строку, регистр не важен.\n"


class UserDictionary:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.words: set[str] = set()
        self.phrases: list[str] = []
        self.load()

    def load(self) -> None:
        self.words, self.phrases = set(), []
        try:
            lines = self.path.read_text(encoding="utf-8-sig").splitlines()
        except FileNotFoundError:
            return
        for line in lines:
            self._remember(line)

    def _remember(self, line: str) -> None:
        entry = line.strip().lower()
        if not entry or entry.startswith("#"):
            return
        if any(ch.isspace() for ch in entry):
            if entry not in self.phrases:
                self.phrases.append(entry)
        else:
            self.words.add(entry)

    def contains(self, word: str) -> bool:
        return word.strip().lower() in self.words

    def covers(self, text: str, start: int, end: int) -> bool:
        lowered = text.lower()
        for phrase in self.phrases:
            position = lowered.find(phrase)
            while position != -1:
                if position <= start and end <= position + len(phrase):
                    return True
                position = lowered.find(phrase, position + 1)
        return False

    def add(self, entry: str) -> None:
        entry = entry.strip()
        if not entry or entry.lower() in self.words or entry.lower() in self.phrases:
            return
        if not self.path.exists():
            self.path.write_text(HEADER, encoding="utf-8")
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(entry + "\n")
        self._remember(entry)
