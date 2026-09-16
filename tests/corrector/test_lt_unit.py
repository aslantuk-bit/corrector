from corrector.core.issue import Category, Level
from corrector.engines import lt


def test_category_map_and_levels():
    assert lt.LT_CATEGORY_MAP["TYPOS"] is Category.SPELLING
    assert lt.LT_CATEGORY_MAP["EXTEND"] is Category.GRAMMAR
    assert lt.level_for(Category.TYPOGRAPHY) is Level.WARNING
    assert lt.level_for(Category.PUNCTUATION) is Level.ERROR


def test_batches_by_length():
    paragraphs = [(0, "а" * 10), (1, "б" * 10), (2, "в" * 25), (3, "г" * 5)]
    result = lt.batches(paragraphs, limit=22)
    assert [[i for i, _ in b] for b in result] == [[0, 1], [2], [3]]


def test_join_batch_offsets():
    text, offsets = lt.join_batch([(4, "Первый."), (7, "Второй.")])
    assert text == "Первый.\n\nВторой."
    assert offsets == [(4, 0, 7), (7, 9, 7)]


def test_map_matches_to_paragraph_coordinates():
    text, offsets = lt.join_batch([(4, "Первый абзац."), (7, "Второй абзац , с ошибкой.")])
    matches = [{
        "offset": text.index(" ,"), "length": 2, "message": "Поставьте пробел после запятой, а не перед ней.",
        "shortMessage": "", "replacements": [{"value": ","}],
        "rule": {"id": "COMMA_PARENTHESIS_WHITESPACE", "category": {"id": "TYPOGRAPHY"}, "issueType": "whitespace"},
    }, {
        "offset": 0, "length": 6, "message": "Проверьте", "shortMessage": "", "replacements": [],
        "rule": {"id": "X", "category": {"id": "STYLE"}},
    }]
    issues = lt.map_matches(matches, offsets)
    assert [(i.paragraph, i.start, i.end, i.category, i.level, i.engine) for i in issues] == [
        (7, 12, 14, Category.TYPOGRAPHY, Level.WARNING, "lt"),
        (4, 0, 6, Category.STYLE, Level.WARNING, "lt"),
    ]
    assert issues[0].suggestions == [","] and issues[0].rule_id == "COMMA_PARENTHESIS_WHITESPACE"


def test_match_crossing_paragraph_boundary_is_dropped():
    text, offsets = lt.join_batch([(0, "Раз."), (1, "Два.")])
    matches = [{"offset": 2, "length": 6, "message": "м", "replacements": [], "rule": {"id": "X", "category": {"id": "MISC"}}}]
    assert lt.map_matches(matches, offsets) == []


def test_load_disabled_rules(tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("# комментарий\nWHITESPACE_RULE\n\n UPPERCASE_SENTENCE_START   # пояснение\n", encoding="utf-8")
    assert lt.load_disabled_rules(p) == ["WHITESPACE_RULE", "UPPERCASE_SENTENCE_START"]
    assert lt.load_disabled_rules(tmp_path / "нет.txt") == []


def test_engine_becomes_unavailable_after_network_error():
    class BrokenClient:
        def check_text(self, text, language="ru-RU"):
            raise lt.LTUnavailable("сервер не отвечает")

    engine = lt.LanguageToolEngine(BrokenClient())
    assert engine.check([(0, "Текст.")]) == []
    status = engine.status()
    assert status.available is False and "сервер не отвечает" in status.note
