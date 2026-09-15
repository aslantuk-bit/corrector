from corrector.core import lang

RU = "Истец обратился в суд с иском о взыскании задолженности по договору, в соответствии со статьёй 5 ГПК."
KK = "Талап қоюшы сотқа шарт бойынша берешекті өндіріп алу туралы талап арызбен жүгінді."
RU_WITH_KK_NAME = "Истец ТОО «Ақ жол» обратился в суд по месту нахождения ответчика в городе Астана."


def test_detect_russian_and_kazakh():
    assert lang.detect(RU) == "ru"
    assert lang.detect(KK) == "kk"


def test_russian_paragraph_with_kazakh_name_stays_russian():
    assert lang.detect(RU_WITH_KK_NAME) == "ru"


def test_kazakh_without_special_letters_by_words():
    assert lang.detect("Сот шешім туралы және талап бойынша") == "kk"


def test_empty_or_numeric_inherits_previous():
    assert lang.detect("", previous="kk") == "kk"
    assert lang.detect("12.05.2024 № 5", previous="ru") == "ru"


def test_detect_all_carries_previous_and_respects_mode():
    texts = [RU, "", KK, "№ 7"]
    assert lang.detect_all(texts) == ["ru", "ru", "kk", "kk"]
    assert lang.detect_all(texts, mode="kk") == ["kk"] * 4


def test_has_kk_letters():
    assert lang.has_kk_letters("Ақ") and not lang.has_kk_letters("Ак")
