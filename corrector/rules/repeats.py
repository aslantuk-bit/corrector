"""Повторы: слово дважды подряд; одно знаменательное слово в соседних предложениях."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext

DOUBLE_RE = re.compile(r"(?<![\w-])([А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]+)\s+\1(?![\w-])", re.IGNORECASE)


class DoubleWordRule(Rule):
    id, lang, category, level = "rep.double", "any", Category.STYLE, Level.ERROR
    message = "Слово повторяется дважды подряд"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        return [make_issue(self, para, m.start(), m.end(), [m.group(1)]) for m in DOUBLE_RE.finditer(para.text)]


NAME_GRAMMEMES = {"Name", "Surn", "Patr", "Geox", "Orgn"}


def looks_like_name(word: str, lang: str, doc: DocContext, text: str) -> bool:
    """Слово с заглавной буквы в начале предложения: имя или обычное слово?"""
    if lang == "kk":
        lowered = word.lower()
        return lowered not in text and word in text[text.find(word) + 1:]
    parses = doc.resources.morph.parse(word)
    return all(not p.is_known for p in parses) or any(g in p.tag for p in parses for g in NAME_GRAMMEMES)


def lemma(word: str, lang: str, doc: DocContext) -> str:
    if lang == "kk":
        return doc.resources.stemmer.stem(word)
    forms = {p.normal_form for p in doc.resources.morph.parse(word)}
    return min(forms, key=len) if forms else word.lower()


class NearRepeatRule(Rule):
    id, lang, category, level = "rep.near", "any", Category.STYLE, Level.HINT
    message = "Повтор слова в соседних предложениях"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        stop = doc.resources.stop_kk if para.lang == "kk" else doc.resources.stop_ru
        issues, previous = [], {}
        for start, end in para.sentences:
            current = {}
            for token in para.words:
                if not (start <= token.start < end) or len(token.text) <= 5:
                    continue
                if token.text[0].isupper() and (token.start != start or looks_like_name(token.text, para.lang, doc, para.text)):
                    continue
                key = lemma(token.text, para.lang, doc)
                if key in stop or token.text.lower() in stop:
                    continue
                current.setdefault(key, token)
            for key, token in current.items():
                if key in previous:
                    issues.append(make_issue(self, para, token.start, token.end,
                                             message=f"Слово «{token.text}» уже было в предыдущем предложении"))
            previous = current
        return issues
