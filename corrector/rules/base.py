"""Базовое правило и фабрика замечаний."""

from __future__ import annotations

from corrector.core.issue import Category, Issue, Level
from corrector.rules.context import DocContext, ParaContext


class Rule:
    id: str = ""
    lang: str = "any"  # ru | kk | any
    category: Category = Category.STYLE
    level: Level = Level.HINT
    message: str = ""
    document_level: bool = False

    def applies(self, lang: str) -> bool:
        return self.lang == "any" or self.lang == lang

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        return []

    def check_document(self, doc: DocContext) -> list[Issue]:
        return []


def make_issue(rule: Rule, para: ParaContext, start: int, end: int, suggestions=(), message: str | None = None,
               engine: str = "rules") -> Issue:
    return Issue(para.index, start, end, rule.category, rule.level, rule.id, engine, message or rule.message, list(suggestions))
