"""Казахская пунктуация и дефисы по правилам emle.kz (үтір § 2, § 10; дефис § 3, § 4, § 7)."""

from __future__ import annotations

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext
from corrector.rules.patterns import PatternRule

CONJUNCTIONS = {"бірақ", "алайда", "дегенмен", "әйтпесе", "әйткенмен", "себебі", "өйткені", "сондықтан"}
CONJ_PAIRS = {("сонда", "да"), ("сол", "себепті")}
# Жалғаулықтар (алайда, дегенмен, сондықтан, сонымен қатар) в начале предложения запятой не требуют — по корпусу
# они пишутся без неё; здесь только қыстырма сөздер.
INTRO = {"мысалы", "әрине", "демек", "біріншіден", "екіншіден", "үшіншіден", "әлбетте", "шамасы", "меніңше", "сірә",
         "бәлкім", "рас", "шынында", "әлбетте"}
INTRO_PAIRS = {("жалпы", "алғанда"), ("атап", "айтқанда"), ("менің", "ойымша"), ("сөз", "жоқ")}
PARTICLES = {"да", "де", "та", "те"}
NOUNS_AFTER_NUMBER = r"(?:ба[пб]|тармақ(?:ша)?|бөлім|тарау|сынып|қабат|орын|то[пб]|санат|деңгей|курс|кезең)"
SUFFIXES = r"(?:н?ші|н?шы|ке|ге|қа|ға|та|те|да|де|ты|ті|ды|ді|тан|тен|дан|ден|нан|нен|ның|нің|дың|дің|тың|тің)"
AFFIXES = {"ның", "нің", "дың", "дің", "тың", "тің", "ке", "ге", "қа", "ға", "та", "те", "да", "де", "ты", "ті", "ды", "ді",
           "тан", "тен", "дан", "ден", "нан", "нен", "мен", "бен", "пен"}


def _nonspace(para: ParaContext):
    return [t for t in para.tokens if t.kind != "space"]


class CommaBeforeConjunctionKkRule(Rule):
    id, lang, category, level = "kk.comma_conj", "kk", Category.PUNCTUATION, Level.ERROR
    message = "Перед союзом нужна запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues, tokens = [], _nonspace(para)
        for i, token in enumerate(tokens):
            if i == 0 or token.kind != "word" or tokens[i - 1].kind != "word":
                continue
            lowered = token.text.lower()
            following = tokens[i + 1].text.lower() if i + 1 < len(tokens) else ""
            if not (lowered in CONJUNCTIONS or (lowered, following) in CONJ_PAIRS):
                continue
            sentence = para.sentence_of(token.start)
            if sentence and sentence[0] == token.start:
                continue
            gap = para.text[tokens[i - 1].end:token.start]
            if gap and gap.strip() == "":
                issues.append(make_issue(self, para, tokens[i - 1].end, token.start, [", "]))
        return issues


class IntroCommaKkRule(Rule):
    id, lang, category, level = "kk.comma_intro", "kk", Category.PUNCTUATION, Level.ERROR
    message = "После вводного слова в начале предложения нужна запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues, tokens = [], _nonspace(para)
        starts = {s for s, _ in para.sentences}
        for i, token in enumerate(tokens):
            if token.kind != "word" or token.start not in starts or i + 1 >= len(tokens):
                continue
            lowered = token.text.lower()
            following = tokens[i + 1]
            if (lowered, following.text.lower()) in INTRO_PAIRS and i + 2 < len(tokens):
                last, nxt = following, tokens[i + 2]
            elif lowered in INTRO:
                last, nxt = token, following
            else:
                continue
            if nxt.kind == "punct":
                continue
            gap = para.text[last.end:nxt.start]
            if gap and gap.strip() == "":
                issues.append(make_issue(self, para, last.end, nxt.start, [", "]))
        return issues


class RepeatedParticleKkRule(Rule):
    id, lang, category, level = "kk.da_de", "kk", Category.PUNCTUATION, Level.HINT
    message = "При повторяющихся частицах да/де/та/те между частями ставится запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for start, end in para.sentences:
            tokens = [t for t in _nonspace(para) if start <= t.start < end]
            positions = [i for i, t in enumerate(tokens) if t.kind == "word" and t.text.lower() in PARTICLES]
            if len(positions) < 2:
                continue
            first, second = positions[0], positions[1]
            between = tokens[first + 1:second]
            if between and all(t.kind == "word" for t in between):
                issues.append(make_issue(self, para, tokens[first].start, tokens[second].end))
        return issues


HYPHEN_RULES = [
    PatternRule("kk.hyphen_ordinal", "kk", Category.TYPOGRAPHY, Level.ERROR, "Между числом и словом ставится дефис: «5-бап»",
                rf"\b(\d+) ({NOUNS_AFTER_NUMBER}[а-яәғқңөұүһі]*)\b", r"\1-\2", flags=0),
    PatternRule("kk.hyphen_suffix", "kk", Category.TYPOGRAPHY, Level.ERROR, "Аффикс после числа пишется через дефис: «5-ші»",
                rf"\b(\d+) ({SUFFIXES})\b", r"\1-\2", flags=0),
    PatternRule("kk.hyphen_abbrev", "kk", Category.TYPOGRAPHY, Level.ERROR, "Аффикс к аббревиатуре пишется через дефис: «ҚР-ның»",
                r"\b([А-ЯӘҒҚҢӨҰҮҺІ]{2,6})([а-яәғқңөұүһі]{2,4})\b", r"\1-\2", flags=0,
                condition=lambda m, p, d: m.group(2) in AFFIXES),
]

PUNCT_KK_RULES: list[Rule] = [CommaBeforeConjunctionKkRule(), IntroCommaKkRule(), RepeatedParticleKkRule(), *HYPHEN_RULES]
