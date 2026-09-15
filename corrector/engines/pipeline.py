"""Конвейер: язык абзацев → движки → фильтры → снятие дублей → сортировка."""

from __future__ import annotations

from corrector.core import lang
from corrector.core.issue import Category, Issue, dedupe
from corrector.core.settings import Settings
from corrector.core.text import words
from corrector.core.userdict import UserDictionary
from corrector.docx_io.model import DocumentModel
from corrector.engines.factory import Engines
from corrector.rules import context


def check_document(model: DocumentModel, engines: Engines, user_dict: UserDictionary, settings: Settings) -> list[Issue]:
    texts = model.texts()
    languages = lang.detect_all(texts, settings.language)
    ru = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "ru" and p.text.strip()]
    kk = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "kk" and p.text.strip()]
    issues: list[Issue] = []
    if ru:
        issues += engines.ru.check(ru)
        for index, text in ru:
            tokens = [t for t in words(text) if lang.has_kk_letters(t.text)]
            if tokens:
                issues += engines.kk_names.check_tokens(index, text, tokens)
    if kk:
        issues += engines.kk.check(kk)
    if engines.rules is not None:
        ctx = context.build_contexts(model, languages, settings, engines.rule_resources)
        issues += engines.rules.run(ctx)
    return dedupe(filter_issues(issues, model, user_dict, settings))


def filter_issues(issues: list[Issue], model: DocumentModel, user_dict: UserDictionary, settings: Settings) -> list[Issue]:
    kept = []
    for issue in issues:
        if not settings.categories.get(issue.category.value, True):
            continue
        if issue.rule_id in settings.disabled_rules:
            continue
        if issue.category is Category.SPELLING:
            text = model.paragraphs[issue.paragraph].text
            fragment = text[issue.start:issue.end]
            if user_dict.contains(fragment) or user_dict.covers(text, issue.start, issue.end):
                continue
        kept.append(issue)
    return kept
