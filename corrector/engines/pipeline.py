"""Конвейер: язык абзацев → движки → фильтры → снятие дублей → сортировка."""

from __future__ import annotations

from collections import Counter

from corrector.core import lang
from corrector.core.issue import Category, Issue, Level, dedupe
from corrector.core.settings import Settings
from corrector.core.text import sentences, words
from corrector.engines.spell import NAME_MESSAGE
from corrector.core.userdict import UserDictionary
from corrector.docx_io.model import DocumentModel
from corrector.engines.factory import Engines
from corrector.rules import context


def check_document(model: DocumentModel, engines: Engines, user_dict: UserDictionary, settings: Settings) -> list[Issue]:
    texts = model.texts()
    languages = lang.detect_all(texts, settings.language)
    ru = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "ru" and p.text.strip()]
    kk = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "kk" and p.text.strip()]
    mixed = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "mixed" and p.text.strip()]
    issues: list[Issue] = []
    for index, text in mixed:  # двуязычный абзац: каждое слово — по своему словарю, без подсказок «русское слово»
        tokens = words(text)
        kk_tokens = [t for t in tokens if lang.has_kk_letters(t.text)]
        # слово без казахских букв может быть казахским (РЕСПУБЛИКАСЫ): русскому словарю отдаём только неизвестные казахскому
        ru_tokens = [t for t in tokens if not lang.has_kk_letters(t.text) and not engines.kk.dictionary.known(t.text)]
        issues += engines.kk.check_tokens(index, text, kk_tokens, foreign_hints=False)
        issues += engines.ru_spell.check_tokens(index, text, ru_tokens)
    if ru:
        issues += refine_lt_spelling(engines.ru.check(ru), ru, engines)
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


def refine_lt_spelling(issues: list[Issue], paragraphs: list[tuple[int, str]], engines: Engines) -> list[Issue]:
    """Орфография LanguageTool через наш словарный движок: лексикон, имена из корпуса и политика имён собственных."""
    texts = dict(paragraphs)
    counts = Counter(t.text for text in texts.values() for t in words(text))
    starts = {index: {s for s, _ in sentences(text)} for index, text in texts.items()}
    kept = []
    for issue in issues:
        if issue.engine != "lt" or issue.category is not Category.SPELLING:
            kept.append(issue)
            continue
        word = texts[issue.paragraph][issue.start:issue.end]
        if not word or engines.ru_spell.accepts(word):
            continue
        if word[0].isupper() and word[1:].islower() and issue.start not in starts[issue.paragraph]:
            if counts[word] >= 2:
                continue
            issue.level, issue.message, issue.suggestions = Level.HINT, NAME_MESSAGE, []
        kept.append(issue)
    return kept


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
