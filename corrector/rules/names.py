"""Разнобой имён и названий: похожие, но не одинаковые слова с заглавной буквы в одном документе."""

from __future__ import annotations

from collections import Counter, defaultdict

from corrector.core.issue import Category, Issue, Level
from corrector.core.text import Token
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext
from corrector.rules.repeats import lemma

KK_NAME_AFFIXES = sorted(["тің", "тың", "дің", "дың", "нің", "ның", "тан", "тен", "дан", "ден", "нан", "нен", "мен", "бен", "пен",
                          "ке", "ге", "қа", "ға", "та", "те", "да", "де", "ты", "ті", "ды", "ді", "на", "не", "сы", "сі", "ы", "і"],
                         key=len, reverse=True)


RU_NAME_ENDINGS = sorted(["ыми", "ими", "ого", "его", "ому", "ему", "ым", "им", "ом", "ем", "ой", "ей", "ую", "юю", "ая", "яя",
                          "ые", "ие", "ых", "их", "а", "у", "е", "и", "ы", "ю", "я"], key=len, reverse=True)
PATRONYMIC = ("ович", "евич", "ьевич", "овна", "евна", "ьевна", "ична", "инична", "ұлы", "қызы", "улы", "кызы")


def _strip(stem: str, endings: list[str], minimum: int = 4) -> str:
    changed = True
    while changed:
        changed = False
        for ending in endings:
            if stem.endswith(ending) and len(stem) - len(ending) >= minimum:
                stem = stem[: -len(ending)]
                changed = True
                break
    return stem


def name_lemma(word: str, lang: str, doc: DocContext) -> str:
    """Основа имени: снимаем падежные окончания и аффиксы, чтобы склонение не считалось разнобоем."""
    stem = word.lower()
    if lang == "kk":
        stem = _strip(stem, KK_NAME_AFFIXES)
    return _strip(stem, RU_NAME_ENDINGS)


def is_patronymic(word: str) -> bool:
    return word.lower().endswith(PATRONYMIC)


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _is_name(token: Token, para: ParaContext) -> bool:
    text = token.text
    if len(text) < 5 or not text[0].isupper() or not text[1:].islower() or is_patronymic(text):
        return False
    sentence = para.sentence_of(token.start)
    return sentence is None or sentence[0] != token.start


class NamesConsistencyRule(Rule):
    id, lang, category, level = "names.variants", "any", Category.STYLE, Level.WARNING
    message = "Похоже на разное написание одного имени"
    document_level = True

    def check_document(self, doc: DocContext) -> list[Issue]:
        occurrences: dict[str, list[tuple[ParaContext, Token]]] = defaultdict(list)
        lemmas: dict[str, str] = {}
        for para in doc.paragraphs:
            for token in para.words:
                if _is_name(token, para):
                    occurrences[token.text].append((para, token))
                    lemmas.setdefault(token.text, name_lemma(token.text, para.lang, doc))
        counts = Counter({form: len(items) for form, items in occurrences.items()})
        by_lemma: dict[str, int] = defaultdict(int)
        for form, n in counts.items():
            by_lemma[lemmas[form]] += n
        issues: list[Issue] = []
        lemma_list = sorted(by_lemma, key=lambda l: -by_lemma[l])
        for i, rare in enumerate(lemma_list):
            for frequent in lemma_list[:i]:
                limit = 1 if len(rare) <= 9 else 2
                if by_lemma[frequent] > by_lemma[rare] and levenshtein(rare, frequent) <= limit:
                    frequent_form = max((f for f in counts if lemmas[f] == frequent), key=counts.get)
                    for form in (f for f in counts if lemmas[f] == rare):
                        suggestion = [frequent_form] if len(form) == len(frequent_form) else []
                        for para, token in occurrences[form]:
                            issues.append(make_issue(
                                self, para, token.start, token.end, suggestion,
                                f"Похоже на разное написание одного имени: «{form}» ({by_lemma[rare]}) и «{frequent_form}» ({by_lemma[frequent]})"))
                    break
        return issues
