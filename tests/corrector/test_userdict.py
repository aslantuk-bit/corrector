from corrector.core.userdict import FILE_NAME, UserDictionary


def test_missing_file_is_empty(tmp_path):
    d = UserDictionary(tmp_path / FILE_NAME)
    assert d.words == set() and d.phrases == []
    assert not d.contains("Ахметов")


def test_load_words_and_phrases(tmp_path):
    (tmp_path / FILE_NAME).write_text("# фамилии\nАхметов\n\nТОО «Ак жол»\n  Нур-Султан  \n", encoding="utf-8")
    d = UserDictionary(tmp_path / FILE_NAME)
    assert d.contains("ахметов") and d.contains("АХМЕТОВ") and d.contains("Нур-Султан")
    assert d.phrases == ["тоо «ак жол»"]


def test_covers_phrase_occurrence(tmp_path):
    (tmp_path / FILE_NAME).write_text("ТОО «Ак жол»\n", encoding="utf-8")
    d = UserDictionary(tmp_path / FILE_NAME)
    text = "Истец ТОО «Ак жол» обратился"
    start = text.index("Ак")
    assert d.covers(text, start, start + 2)
    assert not d.covers(text, 0, 5)


def test_add_appends_and_creates_file(tmp_path):
    d = UserDictionary(tmp_path / FILE_NAME)
    d.add("Ахметов")
    d.add("ТОО «Ак жол»")
    assert d.contains("ахметов")
    text = (tmp_path / FILE_NAME).read_text(encoding="utf-8")
    assert text.startswith("#")
    assert "Ахметов\n" in text and "ТОО «Ак жол»\n" in text
    assert UserDictionary(tmp_path / FILE_NAME).phrases == ["тоо «ак жол»"]


def test_add_ignores_duplicates_and_blank(tmp_path):
    d = UserDictionary(tmp_path / FILE_NAME)
    d.add("Ахметов")
    d.add(" ахметов ")
    d.add("")
    assert (tmp_path / FILE_NAME).read_text(encoding="utf-8").count("хметов") == 1
