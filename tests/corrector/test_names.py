from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.names import NamesConsistencyRule, levenshtein
from tests.corrector.conftest import make_docx


def test_levenshtein():
    assert levenshtein("ахметов", "ахмедов") == 1 and levenshtein("ак жол", "акжол") == 1 and levenshtein("а", "а") == 0


def test_variants_across_paragraphs(tmp_path):
    doc = model.load(make_docx(tmp_path / "д.docx", body=["Истец Ахметов подал иск.", "Ахметов явился, истец Ахметов возражал.", "Ответчик Ахмедов не явился."]))
    d = context.build_contexts(doc, ["ru"] * 3, Settings(), resources.load_resources(paths.data_dir(), tmp_path))
    issues = NamesConsistencyRule().check_document(d)
    assert [(i.paragraph, d.paragraphs[i.paragraph].text[i.start:i.end]) for i in issues] == [(2, "Ахмедов")]
    assert "«Ахмедов» (1) и «Ахметов» (2)" in issues[0].message
    assert issues[0].suggestions == ["Ахметов"]


def test_inflected_forms_are_not_variants(tmp_path):
    doc = model.load(make_docx(tmp_path / "д.docx", body=["Истец Ахметов подал иск. Представитель Ахметова тоже. Повестку Ахметову вручили."]))
    d = context.build_contexts(doc, ["ru"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))
    assert NamesConsistencyRule().check_document(d) == []


def test_common_words_and_fleeting_vowels_are_not_variants(tmp_path):
    doc = model.load(make_docx(tmp_path / "д.docx", body=["Суд заслушал Истца. Заявление Правительство подало. Затем Истец возражал, а Правительства не было. Батыр и Батыс."]))
    d = context.build_contexts(doc, ["ru"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))
    assert NamesConsistencyRule().check_document(d) == []
