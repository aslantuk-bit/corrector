from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.punct_kk import CommaBeforeConjunctionKkRule, IntroCommaKkRule
from tests.corrector.conftest import make_docx


def ctx(tmp_path, text):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    return context.build_contexts(doc, ["kk"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))


def test_conjunction_pairs_and_sentence_start(tmp_path):
    d = ctx(tmp_path, "Шарт жарамсыз сол себепті талап қанағаттандырылмайды. Бірақ бұл маңызды емес.")
    issues = CommaBeforeConjunctionKkRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and d.paragraphs[0].text[issues[0].end:].startswith("сол себепті")


def test_intro_only_at_sentence_start(tmp_path):
    d = ctx(tmp_path, "Сот, мысалы, шартты қарады. Мысалы шарт бойынша.")
    issues = IntroCommaKkRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and d.paragraphs[0].text[issues[0].start:issues[0].end] == " "
