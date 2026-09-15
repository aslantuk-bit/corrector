"""Правило-шаблон: регулярное выражение, замена с группами, условие."""

from __future__ import annotations

import re
from typing import Callable

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext

Condition = Callable[[re.Match, ParaContext, DocContext], bool]


class PatternRule(Rule):
    def __init__(self, id: str, lang: str, category: Category, level: Level, message: str,
                 pattern: str | re.Pattern, replacement: str | None = None, flags: int = re.IGNORECASE,
                 condition: Condition | None = None, engine: str = "rules") -> None:
        self.id, self.lang, self.category, self.level, self.message = id, lang, category, level, message
        self.pattern = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
        self.replacement, self.condition, self.engine = replacement, condition, engine

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues: list[Issue] = []
        for match in self.pattern.finditer(para.text):
            if self.condition is not None and not self.condition(match, para, doc):
                continue
            suggestions = []
            if self.replacement is not None:
                fixed = match.expand(self.replacement)
                if fixed == match.group():
                    continue
                suggestions = [fixed]
            issues.append(make_issue(self, para, match.start(), match.end(), suggestions, engine=self.engine))
        return issues
