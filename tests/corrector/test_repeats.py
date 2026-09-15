from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.repeats import NearRepeatRule
from corrector.rules.sentences import LongSentenceRule
from tests.corrector.conftest import make_docx


def ctx(tmp_path, text, lang="ru", limit=60):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    res = resources.load_resources(paths.data_dir(), tmp_path)
    return context.build_contexts(doc, [lang], Settings(sentence_words_limit=limit), res)


def test_near_repeat_uses_lemmas_and_stoplist(tmp_path):
    d = ctx(tmp_path, "Ответчик представил возражение. Возражение не мотивировано.")
    issues = NearRepeatRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and d.paragraphs[0].text[issues[0].start:issues[0].end] == "Возражение"
    assert "уже было" in issues[0].message
    d = ctx(tmp_path, "Суд рассмотрел дело. Суд решил.")
    assert NearRepeatRule().check(d.paragraphs[0], d) == []


def test_near_repeat_kazakh_stems(tmp_path):
    d = ctx(tmp_path, "Жауапкер қарсылық білдірді. Бұл қарсылықтың негізі жоқ.", "kk")
    assert len(NearRepeatRule().check(d.paragraphs[0], d)) == 1


def test_long_sentence_threshold(tmp_path):
    d = ctx(tmp_path, "раз два три четыре пять шесть. Семь восемь.", limit=5)
    issues = LongSentenceRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and issues[0].message == "Предложение из 6 слов: разбейте на два"
