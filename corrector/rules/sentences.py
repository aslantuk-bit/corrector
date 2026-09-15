"""Длина предложения."""

from __future__ import annotations

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext


class LongSentenceRule(Rule):
    id, lang, category, level = "sent.long", "any", Category.STYLE, Level.HINT
    message = "Слишком длинное предложение"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        limit = doc.settings.sentence_words_limit
        issues = []
        for start, end in para.sentences:
            count = sum(1 for t in para.words if start <= t.start < end)
            if count > limit:
                issues.append(make_issue(self, para, start, end, message=f"Предложение из {count} слов: разбейте на два"))
        return issues
