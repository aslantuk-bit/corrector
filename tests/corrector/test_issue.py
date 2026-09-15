from corrector.core.issue import CATEGORY_TITLES, Category, Issue, Level, dedupe, sort_issues


def make(paragraph=0, start=0, end=5, category=Category.SPELLING, engine="lt", rule="R"):
    return Issue(paragraph, start, end, category, Level.ERROR, rule, engine, "сообщение", ["вариант"])


def test_titles_in_russian():
    assert CATEGORY_TITLES[Category.PUNCTUATION] == "Пунктуация"
    assert Category("spelling") is Category.SPELLING


def test_to_dict_uses_plain_values():
    d = make().to_dict()
    assert d["category"] == "spelling" and d["level"] == "error" and d["suggestions"] == ["вариант"]


def test_sort_by_paragraph_then_position():
    issues = [make(1, 10, 12), make(0, 20, 22), make(0, 5, 9)]
    assert [(i.paragraph, i.start) for i in sort_issues(issues)] == [(0, 5), (0, 20), (1, 10)]


def test_dedupe_keeps_higher_priority_engine_on_overlap():
    lt = make(0, 0, 5, engine="lt", rule="LT")
    rules = make(0, 2, 7, engine="rules", rule="OUR")
    kept = dedupe([lt, rules])
    assert [i.rule_id for i in kept] == ["OUR"]


def test_dedupe_keeps_first_on_equal_priority():
    a = make(0, 0, 5, engine="lt", rule="A")
    b = make(0, 0, 5, engine="lt", rule="B")
    assert [i.rule_id for i in dedupe([a, b])] == ["A"]


def test_dedupe_keeps_different_categories_and_paragraphs():
    a = make(0, 0, 5, category=Category.SPELLING)
    b = make(0, 0, 5, category=Category.TYPOGRAPHY)
    c = make(1, 0, 5, category=Category.SPELLING)
    assert len(dedupe([a, b, c])) == 3
