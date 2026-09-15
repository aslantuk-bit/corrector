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


def detect(text: str, previous: str = "ru") -> str:
    kk, ru = score(text)
    if kk == 0 and ru == 0:
        return previous
    return "kk" if kk > ru else "ru"


def detect_all(texts: list[str], mode: str = "auto") -> list[str]:
    if mode in ("ru", "kk"):
        return [mode] * len(texts)
    result, previous = [], "ru"
    for text in texts:
        previous = detect(text, previous)
        result.append(previous)
    return result
