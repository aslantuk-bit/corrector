import pytest

from corrector.core import paths
from corrector.core.issue import Category, Level
from corrector.core.userdict import UserDictionary
from corrector.engines.hunspell import SpellDictionary
from corrector.engines.spell import SpellEngine, inside_quotes, load_lexicon


@pytest.fixture(scope="module")
def kk_dict():
    return SpellDictionary(paths.data_dir() / "kk" / "kk_KZ")


@pytest.fixture(scope="module")
def ru_dict():
    return SpellDictionary(paths.data_dir() / "ru" / "ru_RU")


def make_kk(tmp_path, kk_dict, ru_dict, lexicon=frozenset(), words=""):
    (tmp_path / "словарь.txt").write_text(words, encoding="utf-8")
    return SpellEngine("kk_spell", kk_dict, set(lexicon), UserDictionary(tmp_path / "словарь.txt"), other=ru_dict,
                       foreign_message="Русское слово в казахском тексте")


def test_load_lexicon(tmp_path):
    p = tmp_path / "л.txt"
    p.write_text("# заголовок\nҚР\n\n ЖШС \n", encoding="utf-8")
    assert load_lexicon(p) == {"қр", "жшс"}
    assert load_lexicon(tmp_path / "нет.txt") == set()


def test_inside_quotes():
    text = "Талап қоюшы «Закон о защите» деп"
    assert inside_quotes(text, text.index("Закон"))
    assert not inside_quotes(text, 0)
    assert not inside_quotes(text, text.index("деп"))


def test_flags_misspelling_with_suggestions(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    issues = engine.check([(3, "Соттын шешімі заңды.")])
    assert len(issues) == 1
    issue = issues[0]
    assert (issue.paragraph, issue.start, issue.end) == (3, 0, 6)
    assert issue.category is Category.SPELLING and issue.level is Level.ERROR
    assert issue.suggestions[0].lower() == "соттың"
    assert issue.engine == "kk_spell" and issue.rule_id == "kk_spell:unknown"


def test_skips_abbreviations_numbers_latin_and_lexicon(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict, lexicon={"жшс"})
    assert engine.check([(0, "ЖШС «Ақ жол» ҚР АҚБтК 5-бабы 2024 ж. Windows email@sud.kz")]) == []


def test_user_dictionary_and_phrases(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict, words="Ахметбекұлы\n")
    assert engine.check([(0, "Ахметбекұлы келді.")]) == []


def test_russian_word_in_kazakh_text_is_hint_outside_quotes(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    issues = engine.check([(0, "Сот ходатайство қарады.")])
    assert len(issues) == 1 and issues[0].level is Level.HINT and issues[0].category is Category.STYLE
    assert issues[0].message == "Русское слово в казахском тексте"
    assert engine.check([(0, "Сот «ходатайство» деген сөзді қарады.")]) == []


def test_hyphenated_word_accepted_by_parts(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    assert engine.check([(0, "Нұр-Сұлтан қаласы")]) == []


def test_check_tokens_only_given_tokens(tmp_path, kk_dict, ru_dict):
    from corrector.core.text import words
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    text = "Истец ТОО «Ақ жол» и Ақметов"
    tokens = [t for t in words(text) if t.text in ("Ақ", "Ақметов")]
    issues = engine.check_tokens(0, text, tokens)
    assert [text[i.start:i.end] for i in issues] == ["Ақметов"]


def test_russian_fallback_engine(tmp_path, ru_dict):
    (tmp_path / "словарь.txt").write_text("", encoding="utf-8")
    engine = SpellEngine("ru_spell", ru_dict, {"гпк", "рк"}, UserDictionary(tmp_path / "словарь.txt"))
    issues = engine.check([(0, "Истец подал ходатайтсво в порядке ст. 5 ГПК РК.")])
    assert [(i.start, i.end) for i in issues] == [(12, 23)]
    assert issues[0].suggestions[0] == "ходатайство"
    assert engine.status().available is True
