"""Прогон правил по документу."""

from __future__ import annotations

from corrector.core.issue import Issue
from corrector.rules.base import Rule
from corrector.rules.context import DocContext
from corrector.rules.resources import RuleResources


class RulesEngine:
    name = "rules"

    def __init__(self, rules: list[Rule], resources: RuleResources | None = None) -> None:
        self.rules = rules
        self.resources = resources or RuleResources()

    def run(self, doc: DocContext) -> list[Issue]:
        issues: list[Issue] = []
        for rule in self.rules:
            if rule.document_level:
                issues += rule.check_document(doc)
        for para in doc.paragraphs:
            if not para.text.strip():
                continue
            for rule in self.rules:
                if not rule.document_level and rule.applies(para.lang):
                    issues += rule.check(para, doc)
        return issues


def default_rules(resources: RuleResources) -> list[Rule]:
    from corrector.rules.alphabets import MixedAlphabetRule, RomanNumeralRule
    from corrector.rules.legal_ru import LEGAL_RU_RULES
    from corrector.rules.names import NamesConsistencyRule
    from corrector.rules.official import OfficialNamesRule
    from corrector.rules.punct_kk import PUNCT_KK_RULES
    from corrector.rules.repeats import DoubleWordRule, NearRepeatRule
    from corrector.rules.sentences import LongSentenceRule
    from corrector.rules.typography import TYPOGRAPHY_RULES

    rules: list[Rule] = []
    rules += TYPOGRAPHY_RULES
    rules += [MixedAlphabetRule(), RomanNumeralRule()]
    rules += [DoubleWordRule(), NearRepeatRule(), LongSentenceRule(), NamesConsistencyRule(), OfficialNamesRule()]
    rules += LEGAL_RU_RULES
    rules += PUNCT_KK_RULES
    rules += list(resources.user_rules)
    return rules
