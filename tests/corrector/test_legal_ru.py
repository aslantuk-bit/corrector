from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.legal_ru import CommaBeforeConjunctionRule, SoglasnoRule
from tests.corrector.conftest import make_docx


def ctx(tmp_path, text):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    return context.build_contexts(doc, ["ru"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))


def test_soglasno_inflects_to_dative(tmp_path):
    d = ctx(tmp_path, "Согласно приказа директора и согласно статьи 5.")
    issues = SoglasnoRule().check(d.paragraphs[0], d)
    assert [(d.paragraphs[0].text[i.start:i.end], i.suggestions) for i in issues] == [("приказа", ["приказу"]), ("статьи", ["статье"])]


def test_comma_rule_positions_and_exceptions(tmp_path):
    d = ctx(tmp_path, "Суд считает что доводы обоснованы, а то что сказано, неважно.")
    issues = CommaBeforeConjunctionRule().check(d.paragraphs[0], d)
    assert len(issues) == 1
    i = issues[0]
    assert d.paragraphs[0].text[i.start:i.end] == " " and i.suggestions == [", "] and i.end == d.paragraphs[0].text.index("что")
