from corrector.core import text


def kinds(s):
    return [(t.text, t.kind) for t in text.tokenize(s)]


def test_tokenize_words_numbers_punct():
    assert kinds("ст. 5-1 ГПК, 2 000 тенге") == [
        ("ст", "word"), (".", "punct"), (" ", "space"), ("5-1", "number"), (" ", "space"), ("ГПК", "word"),
        (",", "punct"), (" ", "space"), ("2", "number"), (" ", "space"), ("000", "number"), (" ", "space"), ("тенге", "word"),
    ]


def test_tokenize_kazakh_and_hyphens():
    assert [t.text for t in text.words("Нұр-Сұлтан қаласының 5-ші бабы")] == ["Нұр-Сұлтан", "қаласының", "бабы"]
    assert [t.text for t in text.tokenize("5-ші")] == ["5-ші"]
    assert text.tokenize("5-ші")[0].kind == "number"


def test_token_offsets():
    tokens = text.words("Суд решил")
    assert (tokens[1].start, tokens[1].end) == (4, 9)


def test_sentences_simple():
    s = "Суд решил. Иск удовлетворить."
    assert [s[a:b] for a, b in text.sentences(s)] == ["Суд решил.", "Иск удовлетворить."]


def test_sentences_keep_abbreviations_and_initials():
    s = "В соответствии со ст. 5 ГПК РК иск подан. Ответчик А. Б. Ахметов не явился."
    assert [s[a:b] for a, b in text.sentences(s)] == [
        "В соответствии со ст. 5 ГПК РК иск подан.", "Ответчик А. Б. Ахметов не явился."]


def test_sentences_list_marker_and_lowercase_continuation():
    s = "1. Рассмотрев дело, суд установил следующее. т.е. иное не доказано."
    assert [s[a:b] for a, b in text.sentences(s)] == ["1. Рассмотрев дело, суд установил следующее. т.е. иное не доказано."]


def test_sentences_question_and_quotes():
    s = "Кто истец? «Ак жол». Ответчик."
    assert [s[a:b] for a, b in text.sentences(s)] == ["Кто истец?", "«Ак жол».", "Ответчик."]


def test_sentences_kazakh_abbreviations():
    s = "Сот шешті. 2024 ж. 5 қаңтардағы шешім жойылсын."
    assert [s[a:b] for a, b in text.sentences(s, "kk")] == ["Сот шешті.", "2024 ж. 5 қаңтардағы шешім жойылсын."]


def test_sentences_without_final_period():
    assert text.sentences("Без точки в конце") == [(0, 17)]
    assert text.sentences("   ") == []
