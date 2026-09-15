"""Замечание: где, что, почему, чем заменить."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Category(str, Enum):
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    PUNCTUATION = "punctuation"
    TYPOGRAPHY = "typography"
    STYLE = "style"


class Level(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    HINT = "hint"


CATEGORY_TITLES = {
    Category.SPELLING: "Орфография",
    Category.GRAMMAR: "Грамматика",
    Category.PUNCTUATION: "Пунктуация",
    Category.TYPOGRAPHY: "Типографика",
    Category.STYLE: "Стиль",
}
LEVEL_TITLES = {Level.ERROR: "ошибка", Level.WARNING: "предупреждение", Level.HINT: "подсказка"}
ENGINE_PRIORITY = {"rules": 0, "user": 0, "lt": 1, "kk_spell": 2, "ru_spell": 2}


@dataclass
class Issue:
    paragraph: int
    start: int
    end: int
    category: Category
    level: Level
    rule_id: str
    engine: str
    message: str
    suggestions: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["category"] = self.category.value
        data["level"] = self.level.value
        return data

    def overlaps(self, other: "Issue") -> bool:
        return self.paragraph == other.paragraph and self.start < other.end and other.start < self.end


def sort_issues(issues: list[Issue]) -> list[Issue]:
    return sorted(issues, key=lambda i: (i.paragraph, i.start, i.end, ENGINE_PRIORITY.get(i.engine, 9)))


def dedupe(issues: list[Issue]) -> list[Issue]:
    """Пересекающиеся замечания одной категории в одном абзаце: остаётся движок с меньшим приоритетом, при равенстве — первое."""
    kept: list[Issue] = []
    for issue in issues:
        priority = ENGINE_PRIORITY.get(issue.engine, 9)
        replaced = False
        for index, other in enumerate(kept):
            if other.category == issue.category and other.overlaps(issue):
                if priority < ENGINE_PRIORITY.get(other.engine, 9):
                    kept[index] = issue
                replaced = True
                break
        if not replaced:
            kept.append(issue)
    return sort_issues(kept)
