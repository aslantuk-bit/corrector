"""Язык абзаца: казахские буквы и частотные слова против частотных русских слов (списки сняты с корпуса актов)."""

from __future__ import annotations

from corrector.core.text import words

KK_LETTERS = set("әғқңөұүһіӘҒҚҢӨҰҮҺІ")
KK_WORDS = {
    "және", "туралы", "бойынша", "сәйкес", "деп", "мен", "осы", "үшін", "немесе", "әрі", "бас", "бұдан", "беру",
    "сот", "іс", "жер", "талап", "жылғы", "сотының", "сотқа", "шешім", "жауапкер", "қоюшы", "республикасының",
    "заңды", "заңсыз", "жеке", "тиіс", "болып", "қаласы", "мемлекеттік", "әкімшілік", "тұрғын", "үй", "кодексінің",
    "бабының", "бабы", "жөніндегі", "арыз", "шарт", "төлеу", "өндіріп", "алу", "бойы", "емес", "бар", "жоқ",
}
RU_WORDS = {
    "и", "в", "во", "на", "по", "с", "со", "не", "что", "от", "для", "при", "об", "о", "или", "из", "за", "его",
    "без", "к", "как", "года", "суд", "суда", "статьи", "дела", "решение", "согласно", "далее", "части", "первой",
    "иска", "истца", "ответчика", "заявитель", "республики", "казахстан", "области", "города", "кодекса",
    "соответствии", "истец", "ответчик", "договору", "договора", "взыскании", "обратился",
}


def has_kk_letters(word: str) -> bool:
    return any(ch in KK_LETTERS for ch in word)


def score(text: str) -> tuple[int, int]:
    kk = sum(1 for ch in text if ch in KK_LETTERS) * 3
    ru = 0
    for token in words(text):
        lowered = token.text.lower()
        if lowered in KK_WORDS:
            kk += 2
        elif lowered in RU_WORDS:
            ru += 2
    return kk, ru


def evidence(text: str) -> tuple[int, int]:
    """Сколько слов явно казахских (казахские буквы или частотное слово) и явно русских (частотное слово)."""
    kk = ru = 0
    for token in words(text):
        lowered = token.text.lower()
        if has_kk_letters(token.text) or lowered in KK_WORDS:
            kk += 1
        elif lowered in RU_WORDS:
            ru += 1
    return kk, ru


def detect(text: str, previous: str = "ru", ru_known=None) -> str:
    """ru, kk или mixed (двуязычная шапка: не меньше трёх явных слов каждого языка).

    ru_known(word) — проверка по русскому словарю: короткий русский абзац с казахским именем
    («при секретаре … Нұрлан А.А.») иначе принимался бы за казахский из-за казахских букв.
    """
    kk, ru = score(text)
    if kk == 0 and ru == 0:
        return previous
    kk_words, ru_words = evidence(text)
    if ru_known is not None:
        ru_words = sum(1 for t in words(text) if not has_kk_letters(t.text) and t.text.lower() not in KK_WORDS
                       and len(t.text) >= 3 and ru_known(t.text))
    if kk_words >= 3 and ru_words >= 3:
        return "mixed"
    if ru_words >= 2 * max(kk_words, 1):
        return "ru"
    if kk_words >= 2 * max(ru_words, 1):
        return "kk"
    return "kk" if kk > ru else "ru"


def detect_all(texts: list[str], mode: str = "auto", ru_known=None) -> list[str]:
    if mode in ("ru", "kk"):
        return [mode] * len(texts)
    result, previous = [], "ru"
    for text in texts:
        code = detect(text, previous, ru_known)
        result.append(code)
        if code != "mixed":
            previous = code
    return result
