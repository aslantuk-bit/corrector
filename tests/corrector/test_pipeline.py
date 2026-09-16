from corrector.core.issue import Category, Issue, Level
from corrector.core.settings import Settings
from corrector.core.userdict import UserDictionary
from corrector.docx_io import model
from corrector.engines import factory, pipeline
from corrector.engines.base import EngineStatus
from tests.corrector.conftest import make_docx


class FakeRu:
    name = "fake_ru"

    def __init__(self):
        self.seen = []

    def check(self, paragraphs):
        self.seen += [i for i, _ in paragraphs]
        return [Issue(i, 0, 5, Category.GRAMMAR, Level.ERROR, "FAKE", "lt", "м") for i, _ in paragraphs]

    def status(self):
        return EngineStatus(self.name, True)


def build(tmp_path, fake_ru):
    engines = factory.build_engines(UserDictionary(tmp_path / "словарь.txt"), no_lt=True)
    engines.ru = fake_ru
    return engines


def test_routes_paragraphs_by_language(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Истец обратился в суд с иском.", "Талап қоюшы сотқа жүгінді."])
    doc = model.load(path)
    fake = FakeRu()
    engines = build(tmp_path, fake)
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    assert fake.seen == [0]
    assert [i.paragraph for i in issues] == [0]


def test_kazakh_misspelling_found_and_russian_name_with_kazakh_letters_checked(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Соттын шешімі заңды.", "Истец Ақметов обратился в суд с иском."])
    doc = model.load(path)
    engines = build(tmp_path, FakeRu())
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    spelling = [(i.paragraph, doc.paragraphs[i.paragraph].text[i.start:i.end]) for i in issues if i.category is Category.SPELLING]
    assert spelling == [(0, "Соттын"), (1, "Ақметов")]


def test_filters_by_settings_and_user_dictionary(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Соттын шешімі заңды."])
    doc = model.load(path)
    engines = build(tmp_path, FakeRu())
    try:
        user = UserDictionary(tmp_path / "словарь.txt")
        settings = Settings()
        settings.categories["spelling"] = False
        assert pipeline.check_document(doc, engines, user, settings) == []
        settings.categories["spelling"] = True
        settings.disabled_rules = ["kk_spell:unknown"]
        assert pipeline.check_document(doc, engines, user, settings) == []
        settings.disabled_rules = []
        user.add("Соттын")
        assert pipeline.check_document(doc, engines, user, settings) == []
    finally:
        engines.close()


def test_forced_language_mode(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Талап қоюшы сотқа жүгінді."])
    doc = model.load(path)
    fake = FakeRu()
    engines = build(tmp_path, fake)
    try:
        pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings(language="ru"))
    finally:
        engines.close()
    assert fake.seen == [0]


def test_rules_run_in_pipeline_and_win_over_lt(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Суд  решил что иск обоснован."])
    doc = model.load(path)
    engines = build(tmp_path, FakeRu())
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    ids = {i.rule_id for i in issues}
    assert {"typo.double_space", "punct.comma_conj"} <= ids
    assert all(i.engine in ("rules", "lt") for i in issues)


def test_user_rules_loaded_from_user_dir(tmp_path):
    (tmp_path / "правила.yaml").write_text("- id: тнг\n  найти: тнг\n  заменить: тенге\n  сообщение: 'Пишите «тенге»'\n", encoding="utf-8")
    path = make_docx(tmp_path / "а.docx", body=["Сумма 500 тнг взыскана."])
    doc = model.load(path)
    engines = factory.build_engines(UserDictionary(tmp_path / "словарь.txt"), no_lt=True, user_dir=tmp_path)
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    assert [(i.rule_id, i.engine, i.suggestions) for i in issues if i.engine == "user"] == [("user.тнг", "user", ["тенге"])]


def test_mixed_paragraph_has_no_foreign_hints_and_checks_both_dictionaries(tmp_path):
    text = "ҚАЗАҚСТАН РЕСПУБЛИКАСЫ ЖОҒАРҒЫ СОТЫ / ВЕРХОВНЫЙ СУД РЕСПУБЛИКИ КАЗАХСТАН, судебная колегия по гражданским делам, сот алқасы шешімі"
    path = make_docx(tmp_path / "а.docx", body=[text])
    doc = model.load(path)
    fake = FakeRu()
    engines = build(tmp_path, fake)
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    assert fake.seen == []
    assert [doc.paragraphs[0].text[i.start:i.end] for i in issues if i.category is Category.SPELLING] == ["колегия"]
    assert not [i for i in issues if i.rule_id.endswith(":foreign")]


class FakeLt:
    """LanguageTool-подобный движок: помечает орфографией каждое слово с заглавной буквы и слово «ходатайтсво»."""

    name = "lt"

    def check(self, paragraphs):
        from corrector.core.text import words
        result = []
        for index, text in paragraphs:
            for token in words(text):
                if token.text[0].isupper() or token.text == "ходатайтсво":
                    result.append(Issue(index, token.start, token.end, Category.SPELLING, Level.ERROR, "MORFOLOGIK_RULE_RU_RU", "lt", "Возможно найдена орфографическая ошибка.", ["вариант"]))
        return result

    def status(self):
        return EngineStatus(self.name, True)


def test_lt_spelling_filtered_by_lexicon_names_and_name_policy(tmp_path):
    body = ["Истец Турматова подала ходатайтсво в акимат Кызылординской области.", "Представитель Турматова явился. Кызылординской."]
    doc = model.load(make_docx(tmp_path / "а.docx", body=body))
    engines = build(tmp_path, FakeLt())
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    spelling = [(doc.paragraphs[i.paragraph].text[i.start:i.end], i.level) for i in issues if i.category is Category.SPELLING]
    # «акимат» — в лексиконе, «Кызылординской» — в списке имён, «Турматова» — дважды: всё это не ошибки;
    # «Истец» и «Представитель» — известны словарю; остаётся настоящая опечатка
    assert spelling == [("ходатайтсво", Level.ERROR)]
