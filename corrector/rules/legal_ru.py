"""Русские юридические шаблоны там, где LanguageTool молчит."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext
from corrector.rules.patterns import PatternRule

TIME_WORDS = r"(?:срока|месяца|месяцев|дня|дней|года|лет|недели|недель|часа|часов|суток|времени|периода|квартала|\d+)"
CONJUNCTIONS = {"что", "чтобы", "который", "которая", "которое", "которые", "которого", "которой", "которым", "которых",
                "которую", "которому", "если", "поскольку", "хотя", "когда"}
PAIRS = {("так", "как"), ("потому", "что")}
EXCEPTIONS = {"то", "вот", "не", "а", "и", "лишь", "только", "едва", "потому", "так", "разве", "ли", "как", "тем",
              "прежде", "после", "до", "перед", "затем", "в", "о", "об", "при", "для", "на", "за", "из", "с", "иное",
              "все", "всё", "тот", "та", "те", "того", "той", "тех", "ни", "же", "бы", "также", "согласно", "случае",
              "даже", "особенно", "именно", "между", "среди", "вследствие", "ввиду", "кроме", "помимо", "против", "у",
              "к", "по", "от", "без", "через", "над", "под", "про", "вместо", "относительно", "касательно"}
WINDOW = 3  # запятая среди предыдущих трёх токенов уже обособила оборот («стороне, в пользу которой»)


def _not_after_privesti(match, para, doc):
    before = para.text[:match.start()].lower()[-60:]
    return not re.search(r"(привест|привед|привод)\w*(\s+\S+){0,3}\s*$", before)


SOOTVETSTVIE = PatternRule("legal.sootvetstvie", "ru", Category.GRAMMAR, Level.ERROR, "Правильно: «в соответствии с»",
                           r"\bв соответствие (с|со)\b", r"в соответствии \1", condition=_not_after_privesti)
V_TECHENIE = PatternRule("legal.v_techenie", "ru", Category.GRAMMAR, Level.ERROR, "О сроке пишется «в течение»",
                         rf"\bв течении(?= {TIME_WORDS}\b)", "в течение")


class SoglasnoRule(Rule):
    id, lang, category, level = "legal.soglasno", "ru", Category.GRAMMAR, Level.ERROR
    message = "После «согласно» — дательный падеж"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for i, token in enumerate(para.words[:-1]):
            if token.text.lower() != "согласно":
                continue
            following = para.words[i + 1]
            parses = doc.resources.morph.parse(following.text)
            if not parses or parses[0].tag.POS not in ("NOUN", "ADJF", "PRTF") or "gent" not in parses[0].tag:
                continue
            if any("datv" in p.tag for p in parses):
                continue
            dative = parses[0].inflect({"datv"})
            suggestion = [dative.word] if dative else []
            issues.append(make_issue(self, para, following.start, following.end, suggestion))
        return issues


class CommaBeforeConjunctionRule(Rule):
    id, lang, category, level = "punct.comma_conj", "ru", Category.PUNCTUATION, Level.ERROR
    message = "Перед союзом нужна запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        tokens = [t for t in para.tokens if t.kind != "space"]
        for i, token in enumerate(tokens):
            if token.kind != "word" or i == 0:
                continue
            previous = tokens[i - 1]
            if previous.kind != "word":
                continue
            sentence = para.sentence_of(token.start)
            if sentence and sentence[0] == token.start:
                continue
            lowered = token.text.lower()
            pair = (lowered, tokens[i + 1].text.lower()) if i + 1 < len(tokens) else None
            if pair not in PAIRS and lowered not in CONJUNCTIONS:
                continue
            if pair not in PAIRS and previous.text.lower() in EXCEPTIONS:
                continue
            if any(t.kind == "punct" and t.text in ",;:—–-(«" for t in tokens[max(0, i - WINDOW):i]):
                continue
            gap_start, gap_end = previous.end, token.start
            if gap_end > gap_start and para.text[gap_start:gap_end].strip() == "":
                issues.append(make_issue(self, para, gap_start, gap_end, [", "]))
        return issues


LEGAL_RU_RULES: list[Rule] = [SOOTVETSTVIE, V_TECHENIE, SoglasnoRule(), CommaBeforeConjunctionRule()]
