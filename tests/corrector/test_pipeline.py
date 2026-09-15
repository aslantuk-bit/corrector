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
